"""
PDF parser — extracts text and tables from financial documents.
Uses PyMuPDF for text and pdfplumber for tables.
"""

import re
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
# Table Formatting & Filtering
# ──────────────────────────────────────────────

def format_table_as_text(table: list[list]) -> str:
    """Convert a table (list of rows) into pipe-separated text."""
    rows = []
    for row in table:
        cleaned = [str(cell).strip() if cell else "" for cell in row]
        rows.append(" | ".join(cleaned))
    return "\n".join(rows)


def _is_meaningful_table(table: list[list], table_text: str) -> bool:
    """Filter out junk tables that pdfplumber misdetects.

    Annual reports are full of decorative elements, page headers/footers,
    and tiny fragments that pdfplumber picks up as 'tables'. This function
    ensures we only keep real financial data tables.

    Criteria for a meaningful table:
    - At least 150 characters (not a tiny header)
    - At least 3 rows (header + 2 data rows minimum)
    - At least 2 columns in most rows (not a single-column list)
    - Contains at least one number (financial tables always have numbers)
    """
    # Too short — probably a header, caption, or label
    if len(table_text.strip()) < 150:
        return False

    # Too few rows — not a real data table
    if len(table) < 3:
        return False

    # Must have at least 2 non-empty columns in most rows
    multi_col_rows = sum(
        1 for row in table
        if len([c for c in row if c and str(c).strip()]) >= 2
    )
    if multi_col_rows < 2:
        return False

    # Must contain at least one number (financial tables always have numbers)
    if not re.search(r'\d+[.,]?\d*', table_text):
        return False

    return True


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
    # Track seen content to avoid near-duplicate tables
    seen_table_hashes: set[str] = set()
    tables_skipped = 0

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            try:
                tables = page.extract_tables()
                for table in tables:
                    table_text = format_table_as_text(table)

                    # Skip junk tables (headers, tiny fragments, decorative elements)
                    if not _is_meaningful_table(table, table_text):
                        tables_skipped += 1
                        continue

                    # Skip near-duplicate tables (same first 200 chars)
                    table_hash = table_text[:200].strip()
                    if table_hash in seen_table_hashes:
                        tables_skipped += 1
                        continue
                    seen_table_hashes.add(table_hash)

                    result["tables"].append({
                        "page": page_num + 1,
                        "data": table,
                        "text": table_text,
                    })
            except Exception:
                continue

    if tables_skipped > 0:
        print(f"   🧹 Filtered out {tables_skipped} junk/duplicate tables, "
              f"kept {len(result['tables'])} meaningful tables")

    return result