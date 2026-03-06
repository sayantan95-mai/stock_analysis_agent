"""
RAG pipeline — orchestrates ingestion (PDF → chunks → vectors)
and retrieval (query → relevant chunks → LLM answer).
"""

from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config.settings import settings
from src.tools.pdf_parser import parse_pdf, classify_sections, format_table_as_text
from src.rag.vector_store import store_chunks, query_chunks
from src.models.schemas import DocumentSummary


# ──────────────────────────────────────────────
# Query → Section Routing
# ──────────────────────────────────────────────

QUERY_TO_SECTION: dict[str, str] = {
    "revenue":        "revenue",
    "sales":          "revenue",
    "turnover":       "revenue",
    "profit":         "profit_loss",
    "loss":           "profit_loss",
    "ebitda":         "profit_loss",
    "pat":            "profit_loss",
    "debt":           "balance_sheet",
    "assets":         "balance_sheet",
    "liabilities":    "balance_sheet",
    "equity":         "balance_sheet",
    "net worth":      "balance_sheet",
    "cash flow":      "cash_flow",
    "free cash flow": "cash_flow",
    "risk":           "risk_factors",
    "outlook":        "management_discussion",
    "strategy":       "management_discussion",
    "management":     "management_discussion",
    "promoter":       "shareholding",
    "fii":            "shareholding",
    "roe":            "ratios",
    "roce":           "ratios",
    "eps":            "ratios",
    "ratio":          "ratios",
    "segment":        "segment_info",
}


def detect_section(query: str) -> str | None:
    """Auto-detect which section to filter by based on query keywords."""
    query_lower = query.lower()
    for keyword, section in QUERY_TO_SECTION.items():
        if keyword in query_lower:
            return section
    return None


# ──────────────────────────────────────────────
# INGESTION PIPELINE
# ──────────────────────────────────────────────

def ingest_document(
    pdf_path: str | Path,
    company: str,
    doc_type: str = "annual_report",
    period: str = "FY2024",
) -> DocumentSummary:
    """
    Full ingestion pipeline:
    PDF → Parse → Smart Chunk → Classify → Embed → Store in ChromaDB.

    Args:
        pdf_path: Path to the PDF file.
        company: Company name.
        doc_type: "annual_report" or "quarterly".
        period: Time period (e.g., "FY2024", "Q3_FY2024").

    Returns:
        DocumentSummary with stats about what was ingested.
    """
    pdf_path = Path(pdf_path)

    # Step 1: Parse PDF
    parsed = parse_pdf(pdf_path)

    # Step 2: Smart chunking
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n\n", "\n\n", "\n", ". "],
    )

    all_chunks: list[dict] = []
    all_sections_found: set[str] = set()

    # --- Tables: keep as single chunks (never split) ---
    for table_info in parsed["tables"]:
        table_text = table_info["text"]
        sections = classify_sections(table_text)
        all_sections_found.update(sections)
        all_chunks.append({
            "content": table_text,
            "metadata": {
                "company": company,
                "doc_type": doc_type,
                "period": period,
                "page": table_info["page"],
                "content_type": "table",
                "sections": sections,
            },
        })

    # --- Text: section-aware splitting ---
    for page_info in parsed["text_pages"]:
        text = page_info["content"]
        if len(text.strip()) < 50:
            continue

        sub_chunks = splitter.split_text(text)
        for chunk_text in sub_chunks:
            if len(chunk_text.strip()) < 50:
                continue
            sections = classify_sections(chunk_text)
            all_sections_found.update(sections)
            all_chunks.append({
                "content": chunk_text,
                "metadata": {
                    "company": company,
                    "doc_type": doc_type,
                    "period": period,
                    "page": page_info["page"],
                    "content_type": "text",
                    "sections": sections,
                },
            })

    # Step 3: Embed and store
    stored_count = store_chunks(company, all_chunks)

    return DocumentSummary(
        filename=pdf_path.name,
        doc_type=doc_type,
        period=period,
        total_chunks=stored_count,
        key_metrics_found=sorted(all_sections_found),
    )


# ──────────────────────────────────────────────
# RETRIEVAL PIPELINE
# ──────────────────────────────────────────────

def retrieve(
    company: str,
    query: str,
    n_results: int | None = None,
    auto_filter: bool = True,
    period: str | None = None,
) -> list[dict]:
    """
    Retrieve relevant document chunks for a query.

    Args:
        company: Company name.
        query: Natural language question.
        n_results: How many chunks to return.
        auto_filter: Auto-detect section filter from query keywords.
        period: Optional specific period to filter by.

    Returns:
        List of relevant chunks with content, metadata, and score.
    """
    section_filter = detect_section(query) if auto_filter else None

    return query_chunks(
        company=company,
        query=query,
        n_results=n_results,
        section_filter=section_filter,
        period_filter=period,
    )


def retrieve_multi_query(
    company: str,
    queries: list[str],
    n_per_query: int = 4,
) -> list[dict]:
    """
    Retrieve chunks for multiple sub-queries and deduplicate.
    Useful for complex questions that span multiple sections.

    Args:
        company: Company name.
        queries: List of sub-queries.
        n_per_query: Chunks to retrieve per sub-query.

    Returns:
        Deduplicated list of relevant chunks, sorted by relevance.
    """
    seen_content: set[str] = set()
    all_results: list[dict] = []

    for query in queries:
        results = retrieve(company, query, n_results=n_per_query)
        for r in results:
            # Deduplicate by content hash
            content_key = r["content"][:100]
            if content_key not in seen_content:
                seen_content.add(content_key)
                all_results.append(r)

    # Sort by relevance score (highest first)
    all_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    return all_results


# ──────────────────────────────────────────────
# CONTEXT BUILDER (for LLM prompts)
# ──────────────────────────────────────────────

def build_context(chunks: list[dict], max_chunks: int = 10) -> str:
    """
    Format retrieved chunks into a context string for the LLM.

    Args:
        chunks: Retrieved chunks from the vector store.
        max_chunks: Maximum chunks to include.

    Returns:
        Formatted context string with source references.
    """
    if not chunks:
        return "No relevant document sections found."

    parts = []
    for i, chunk in enumerate(chunks[:max_chunks]):
        meta = chunk.get("metadata", {})
        source = (
            f"[Source: {meta.get('doc_type', '?')} | "
            f"{meta.get('period', '?')} | "
            f"Page {meta.get('page', '?')} | "
            f"Section: {meta.get('sections', '?')} | "
            f"Type: {meta.get('content_type', 'text')}]"
        )
        score = chunk.get("relevance_score", 0)
        parts.append(
            f"--- Chunk {i + 1} (relevance: {score:.2f}) {source} ---\n"
            f"{chunk['content']}"
        )

    return "\n\n".join(parts)
