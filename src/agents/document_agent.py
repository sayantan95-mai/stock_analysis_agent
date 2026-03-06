"""
Document Agent — manages financial documents and RAG queries.
"""
from pathlib import Path
from google import genai
from src.config.settings import settings
from src.rag.pipeline import ingest_document, retrieve, build_context


class DocumentAgent:
    def __init__(self):
        self.client = genai.Client(api_key=settings.google_api_key)
        self.ingested_companies: set[str] = set()  # track what's been loaded this session
        self.ingestion_errors: dict[str, str] = {}  # track failures for debugging

    def ingest(self, pdf_path: str, company: str, doc_type: str = "annual_report", period: str = "FY2024") -> dict:
        """Process a PDF and store it in the vector DB.

        Args:
            pdf_path: Path to the PDF file.
            company: Company name.
            doc_type: "annual_report", "quarterly", "earnings_call", etc.
            period: Time period (e.g., "FY2024", "Q3_FY2024").

        Returns:
            Summary dict on success, error dict on failure.
        """
        print(f"📄 [Document Agent] Ingesting {Path(pdf_path).name} ({doc_type}, {period}) for {company}...")

        try:
            summary = ingest_document(
                pdf_path=pdf_path,
                company=company,
                doc_type=doc_type,
                period=period,
            )
            self.ingested_companies.add(company.lower())
            print(f"✅ [Document Agent] Successfully ingested {Path(pdf_path).name}")
            return summary.model_dump()

        except Exception as e:
            error_msg = f"Failed to ingest {Path(pdf_path).name}: {str(e)}"
            print(f"❌ [Document Agent] {error_msg}")
            self.ingestion_errors[pdf_path] = error_msg
            # Still mark as attempted so we can provide feedback
            raise  # Re-raise so orchestrator knows it failed

    def has_documents(self, company: str) -> bool:
        """Check if any documents have been ingested for a company.
        
        Uses multiple checks:
        1. In-memory session tracking
        2. Actual vector store query (more reliable)
        """
        company_lower = company.lower()
        
        # Quick check: session memory
        if company_lower in self.ingested_companies:
            return True
        
        # Thorough check: query the actual vector store
        try:
            # Try to retrieve any chunks for this company
            # FIX: changed 'top_k' to 'n_results' to match retrieve() signature
            chunks = retrieve(company, "company overview financial summary", n_results=1)
            if chunks:
                # Found data in vector store, update session tracking
                self.ingested_companies.add(company_lower)
                return True
        except Exception as e:
            print(f"⚠️ [Document Agent] Vector store check failed: {e}")
        
        return False
    
    def get_ingestion_status(self) -> dict:
        """Return status of document ingestion for debugging."""
        return {
            "ingested_companies": list(self.ingested_companies),
            "errors": self.ingestion_errors,
        }

    def ask(self, company: str, question: str) -> str:
        """Answer a question using RAG (Retrieval Augmented Generation)."""

        # 1. Retrieve relevant chunks
        chunks = retrieve(company, question)

        if not chunks:
            return "I couldn't find any information about that in the uploaded documents."

        # 2. Build Context
        context_text = build_context(chunks)

        # 3. Generate Answer
        system_prompt = """You are a strict financial analyst helper.
        Answer the user's question based ONLY on the provided Document Context.
        - Cite the specific document period/section if possible.
        - Always use specific numbers from the documents.
        - Express amounts in ₹ crore for Indian companies.
        - If the answer is not in the context, say 'Data not found in documents'."""

        user_prompt = f"""
        CONTEXT FROM DOCUMENTS:
        {context_text}

        QUESTION: {question}
        """

        response = self.client.models.generate_content(
            model=settings.gemini_model,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.2,
            ),
            contents=user_prompt,
        )

        return response.text