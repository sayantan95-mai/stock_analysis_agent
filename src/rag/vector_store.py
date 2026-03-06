"""
Vector store — ChromaDB wrapper for storing and querying document embeddings.
"""
from __future__ import annotations

import chromadb
from google import genai

from src.config.settings import settings


# ──────────────────────────────────────────────
# Clients (lazy-initialized)
# ──────────────────────────────────────────────

_chroma_client: chromadb.PersistentClient | None = None
_genai_client: genai.Client | None = None


def _get_chroma() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.chroma_db_path)
    return _chroma_client


def _get_genai() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(api_key=settings.google_api_key)
    return _genai_client


# ──────────────────────────────────────────────
# Embedding
# ──────────────────────────────────────────────

def get_embedding(text: str) -> list[float]:
    """Get embedding vector from Gemini text-embedding-004."""
    client = _get_genai()
    result = client.models.embed_content(
        model=settings.embedding_model,
        content=text,
    )
    return result.embeddings[0].values


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Batch embed multiple texts in one API call (more efficient)."""
    client = _get_genai()
    result = client.models.embed_content(
        model=settings.embedding_model,
        content=texts,
    )
    return [e.values for e in result.embeddings]


# ──────────────────────────────────────────────
# Collection Management
# ──────────────────────────────────────────────

def _collection_name(company: str) -> str:
    """Sanitize company name into a valid ChromaDB collection name.
    Rules: 3-63 chars, [a-zA-Z0-9._-], must start and end with alphanumeric.
    """
    name = company.lower().strip()
    name = name.replace(" ", "-").replace("&", "and")
    # Keep only allowed characters
    name = "".join(c for c in name if c.isalnum() or c in "._-")
    # Strip non-alphanumeric from start and end
    name = name.strip("._-")
    if len(name) < 3:
        name = "co-" + name if name else "company"
    return name[:63]


def get_or_create_collection(company: str) -> chromadb.Collection:
    """Get or create a ChromaDB collection for a company."""
    chroma = _get_chroma()
    return chroma.get_or_create_collection(
        name=_collection_name(company),
        metadata={"hnsw:space": "cosine"},
    )


def delete_collection(company: str) -> None:
    """Delete all stored data for a company."""
    chroma = _get_chroma()
    name = _collection_name(company)
    try:
        chroma.delete_collection(name)
    except ValueError:
        pass  # collection doesn't exist


# ──────────────────────────────────────────────
# Store Chunks
# ──────────────────────────────────────────────

def store_chunks(
    company: str,
    chunks: list[dict],
) -> int:
    """
    Embed and store document chunks in ChromaDB.

    Args:
        company: Company name.
        chunks: List of dicts with "content" and "metadata" keys.
                metadata must be flat (no nested lists/dicts).

    Returns:
        Number of chunks stored.
    """
    collection = get_or_create_collection(company)

    # Batch embed all chunks
    texts = [c["content"] for c in chunks]
    embeddings = get_embeddings_batch(texts)

    ids = []
    documents = []
    metadatas = []

    base_id = _collection_name(company)
    existing_count = collection.count()

    for i, chunk in enumerate(chunks):
        idx = existing_count + i
        ids.append(f"{base_id}_{idx}")
        documents.append(chunk["content"])

        # Flatten metadata — ChromaDB only supports str/int/float/bool
        meta = {}
        for k, v in chunk.get("metadata", {}).items():
            if isinstance(v, list):
                meta[k] = ",".join(str(x) for x in v)
            else:
                meta[k] = v
        metadatas.append(meta)

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    return len(chunks)


# ──────────────────────────────────────────────
# Query / Retrieve
# ──────────────────────────────────────────────

def query_chunks(
    company: str,
    query: str,
    n_results: int | None = None,
    section_filter: str | None = None,
    period_filter: str | None = None,
) -> list[dict]:
    """
    Retrieve the most relevant chunks for a query.

    Args:
        company: Company name.
        query: Natural language query.
        n_results: Number of chunks to return (default from settings).
        section_filter: Optional section tag to filter by (e.g., "revenue").
        period_filter: Optional period to filter by (e.g., "Q3_FY2024").

    Returns:
        List of dicts with "content", "metadata", and "relevance_score".
    """
    if n_results is None:
        n_results = settings.retrieval_top_k

    collection = get_or_create_collection(company)

    if collection.count() == 0:
        return []

    query_embedding = get_embedding(query)

    # Build where filter
    where_filter = None
    conditions = []
    if section_filter:
        conditions.append({"sections": {"$contains": section_filter}})
    if period_filter:
        conditions.append({"period": {"$eq": period_filter}})

    if len(conditions) == 1:
        where_filter = conditions[0]
    elif len(conditions) > 1:
        where_filter = {"$and": conditions}

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        # Retry without filters if filter causes issues
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

    # Package results
    retrieved = []
    if results["ids"] and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            retrieved.append({
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "relevance_score": round(1 - results["distances"][0][i], 4),
            })

    return retrieved