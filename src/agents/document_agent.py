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
        self.ingested_companies: set[str] = set()  # track what's been loaded

    def ingest(self, pdf_path: str, company: str, doc_type: str = "annual_report", period: str = "FY2024") -> dict:
        """Process a PDF and store it in the vector DB.

        Args:
            pdf_path: Path to the PDF file.
            company: Company name.
            doc_type: "annual_report", "quarterly", "earnings_call", etc.
            period: Time period (e.g., "FY2024", "Q3_FY2024").
        """
        print(f"📄 [Document Agent] Ingesting {Path(pdf_path).name} ({doc_type}, {period}) for {company}...")

        summary = ingest_document(
            pdf_path=pdf_path,
            company=company,
            doc_type=doc_type,
            period=period,
        )
        self.ingested_companies.add(company.lower())
        return summary.model_dump()

    def has_documents(self, company: str) -> bool:
        """Check if any documents have been ingested for a company."""
        return company.lower() in self.ingested_companies

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
