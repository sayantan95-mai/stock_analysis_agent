"""
Vector store — ChromaDB wrapper for storing and querying document embeddings.
"""
from __future__ import annotations

import time
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

# Google's BatchEmbedContents API allows at most 100 items per request
_EMBED_BATCH_LIMIT = 100

# Rate-limit: free tier = 100 requests/min. We pause between batches.
_BATCH_DELAY_SECONDS = 2        # small delay between every batch
_RATE_LIMIT_MAX_RETRIES = 5     # max retries on 429 errors


def get_embedding(text: str) -> list[float]:
    """Get embedding vector from Gemini embedding model."""
    client = _get_genai()
    result = client.models.embed_content(
        model=settings.embedding_model,
        contents=text,
    )
    return result.embeddings[0].values


def _embed_batch_with_retry(texts: list[str]) -> list[list[float]]:
    """Embed a single batch (<=100 texts) with retry on rate-limit errors."""
    client = _get_genai()

    for attempt in range(_RATE_LIMIT_MAX_RETRIES):
        try:
            result = client.models.embed_content(
                model=settings.embedding_model,
                contents=texts,
            )
            return [e.values for e in result.embeddings]

        except Exception as e:
            error_str = str(e)
            # Check if it's a rate-limit (429) error
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                # Exponential backoff: 30s, 60s, 120s, 120s, 120s
                wait_time = min(30 * (2 ** attempt), 120)
                print(f"   ⏳ Rate limited (attempt {attempt + 1}/{_RATE_LIMIT_MAX_RETRIES}). "
                      f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                raise  # Non-rate-limit error, don't retry

    raise RuntimeError(
        f"Embedding failed after {_RATE_LIMIT_MAX_RETRIES} retries due to rate limiting. "
        f"Try uploading fewer/smaller documents, or upgrade your Gemini API plan."
    )


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Batch embed multiple texts, respecting the 100-per-request API limit
    and handling rate-limit (429) errors with automatic retry."""
    all_embeddings: list[list[float]] = []
    total_batches = (len(texts) + _EMBED_BATCH_LIMIT - 1) // _EMBED_BATCH_LIMIT

    for batch_num, i in enumerate(range(0, len(texts), _EMBED_BATCH_LIMIT), 1):
        batch = texts[i : i + _EMBED_BATCH_LIMIT]

        if total_batches > 1:
            print(f"   📦 Embedding batch {batch_num}/{total_batches} ({len(batch)} chunks)...")

        embeddings = _embed_batch_with_retry(batch)
        all_embeddings.extend(embeddings)

        # Small delay between batches to stay under rate limits
        if batch_num < total_batches:
            time.sleep(_BATCH_DELAY_SECONDS)

    return all_embeddings


# ──────────────────────────────────────────────
# Collection Management
# ──────────────────────────────────────────────

def _collection_name(company: str) -> str:
    """Sanitize company name into a valid ChromaDB collection name.
    Rules: 3-63 chars, [a-zA-Z0-9._-], must start and end with alphanumeric.
    """
    name = company.lower().strip()
    name = name.replace(" ", "-").replace("&", "and")
    name = "".join(c for c in name if c.isalnum() or c in "._-")
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
        pass


# ──────────────────────────────────────────────
# Store Chunks
# ──────────────────────────────────────────────

_CHROMA_BATCH_LIMIT = 100


def store_chunks(
    company: str,
    chunks: list[dict],
) -> int:
    """
    Embed and store document chunks in ChromaDB.

    Args:
        company: Company name.
        chunks: List of dicts with "content" and "metadata" keys.

    Returns:
        Number of chunks stored.
    """
    collection = get_or_create_collection(company)

    # Batch embed all chunks (handles >100 and rate limits internally)
    texts = [c["content"] for c in chunks]
    embeddings = get_embeddings_batch(texts)

    base_id = _collection_name(company)
    existing_count = collection.count()

    all_ids = []
    all_documents = []
    all_metadatas = []

    for i, chunk in enumerate(chunks):
        idx = existing_count + i
        all_ids.append(f"{base_id}_{idx}")
        all_documents.append(chunk["content"])

        # Flatten metadata — ChromaDB only supports str/int/float/bool
        meta = {}
        for k, v in chunk.get("metadata", {}).items():
            if isinstance(v, list):
                meta[k] = ",".join(str(x) for x in v)
            else:
                meta[k] = v
        all_metadatas.append(meta)

    # Add to ChromaDB in batches
    for i in range(0, len(all_ids), _CHROMA_BATCH_LIMIT):
        end = i + _CHROMA_BATCH_LIMIT
        collection.add(
            ids=all_ids[i:end],
            embeddings=embeddings[i:end],
            documents=all_documents[i:end],
            metadatas=all_metadatas[i:end],
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
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

    retrieved = []
    if results["ids"] and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            retrieved.append({
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "relevance_score": round(1 - results["distances"][0][i], 4),
            })

    return retrieved