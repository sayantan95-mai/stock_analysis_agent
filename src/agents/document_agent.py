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

    def ingest(self, pdf_path: str, company: str, period: str) -> dict:
        """Process a PDF and store it in the vector DB."""
        print(f"📄 [Document Agent] Ingesting {Path(pdf_path).name} for {company}...")
        
        summary = ingest_document(
            pdf_path=pdf_path,
            company=company,
            period=period
        )
        return summary.model_dump()

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
                temperature=0.2
            ),
            contents=user_prompt
        )
        
        return response.text