"""
PDF parser — extracts text and tables from financial documents.
Uses PyMuPDF for text and pdfplumber for tables.
"""

from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber

from src.models.schemas import DocumentChunk


# ──────────────────────────────────────────────
# Section Classification
# ──────────────────────────────────────────────

SECTION_KEYWORDS: dict[str, list[str]] = {
    "revenue":               ["revenue", "turnover", "sales", "income from operations",
                              "top line", "gross revenue"],
    "profit_loss":           ["profit", "loss", "net income", "EBITDA", "PAT", "PBT",
                              "operating profit", "bottom line"],
    "balance_sheet":         ["assets", "liabilities", "equity", "balance sheet",
                              "net worth", "shareholders fund"],
    "cash_flow":             ["cash flow", "operating activities", "investing activities",
                              "financing activities", "free cash flow"],
    "management_discussion": ["MD&A", "management discussion", "outlook", "strategy",
                              "chairman", "director report", "business overview"],
    "risk_factors":          ["risk", "contingent", "litigation", "uncertainty",
                              "going concern"],
    "ratios":                ["ratio", "ROE", "ROCE", "debt to equity", "EPS",
                              "current ratio", "interest coverage"],
    "segment_info":          ["segment", "business wise", "division", "vertical",
                              "geography wise"],
    "shareholding":          ["shareholding", "promoter", "FII", "DII", "public holding",
                              "institutional"],
}


def classify_sections(text: str) -> list[str]:
    """Tag text with all matching financial section labels."""
    text_lower = text.lower()
    tags = []
    for section, keywords in SECTION_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            tags.append(section)
    return tags if tags else ["general"]


# ──────────────────────────────────────────────
# Table Formatting
# ──────────────────────────────────────────────

def format_table_as_text(table: list[list]) -> str:
    """Convert a table (list of rows) into pipe-separated text."""
    rows = []
    for row in table:
        cleaned = [str(cell).strip() if cell else "" for cell in row]
        rows.append(" | ".join(cleaned))
    return "\n".join(rows)


# ──────────────────────────────────────────────
# PDF Parsing
# ──────────────────────────────────────────────

def parse_pdf(pdf_path: str | Path) -> dict:
    """
    Extract text and tables from a financial PDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Dict with "text_pages" and "tables" lists.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    result: dict = {"text_pages": [], "tables": [], "filename": pdf_path.name}

    # --- Text extraction via PyMuPDF (fast, preserves layout) ---
    doc = fitz.open(str(pdf_path))
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            result["text_pages"].append({
                "page": page_num + 1,
                "content": text,
            })
    doc.close()

    # --- Table extraction via pdfplumber (better table detection) ---
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            try:
                tables = page.extract_tables()
                for table in tables:
                    table_text = format_table_as_text(table)
                    if len(table_text.strip()) > 50:  # skip tiny/empty tables
                        result["tables"].append({
                            "page": page_num + 1,
                            "data": table,
                            "text": table_text,
                        })
            except Exception:
                continue  # some pages may fail table extraction

    return result


def create_chunks_from_pdf(
    pdf_path: str | Path,
    company: str,
    doc_type: str,
    period: str,
) -> list[DocumentChunk]:
    """
    Parse a PDF and return classified, chunked DocumentChunk objects.
    Note: This does basic page-level chunking. The RAG pipeline
    applies smarter splitting via langchain text splitters.

    Args:
        pdf_path: Path to the PDF.
        company: Company name (e.g., "Reliance Industries").
        doc_type: Document type (e.g., "annual_report", "quarterly").
        period: Time period (e.g., "FY2024", "Q3_FY2024").

    Returns:
        List of DocumentChunk objects ready for embedding.
    """
    parsed = parse_pdf(pdf_path)
    chunks: list[DocumentChunk] = []

    # --- Tables as single chunks (never split) ---
    for table_info in parsed["tables"]:
        sections = classify_sections(table_info["text"])
        chunks.append(DocumentChunk(
            content=table_info["text"],
            page=table_info["page"],
            content_type="table",
            sections=sections,
            doc_type=doc_type,
            period=period,
        ))

    # --- Text pages (will be further split by RAG pipeline) ---
    for page_info in parsed["text_pages"]:
        sections = classify_sections(page_info["content"])
        chunks.append(DocumentChunk(
            content=page_info["content"],
            page=page_info["page"],
            content_type="text",
            sections=sections,
            doc_type=doc_type,
            period=period,
        ))

    return chunks
