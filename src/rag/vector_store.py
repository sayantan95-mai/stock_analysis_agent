"""
Vector store — ChromaDB wrapper for storing and querying document embeddings.

FREE TIER LIMITS (Gemini Embedding 1):
  - RPM:  100 requests/min
  - TPM:  30,000 tokens/min   ← THIS is the real bottleneck
  - RPD:  1,000 requests/day  ← Hard daily cap

Each text in a batch = 1 request + its tokens toward TPM.
A batch of 25 chunks × ~500 tokens = 12,500 tokens (safely under 30K TPM).
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
# Embedding — Rate-Limit-Aware
# ──────────────────────────────────────────────

# Batch size 25: at ~500 tokens/chunk → ~12,500 tokens/batch (under 30K TPM)
# Also only 25 RPM used per batch (under 100 RPM)
_EMBED_BATCH_LIMIT = 25

# Wait 62s between batches so RPM counter fully resets
_BATCH_DELAY_SECONDS = 62

# Max retries on 429 errors
_RATE_LIMIT_MAX_RETRIES = 3


def get_embedding(text: str) -> list[float]:
    """Get embedding vector for a single text."""
    client = _get_genai()
    result = client.models.embed_content(
        model=settings.embedding_model,
        contents=text,
    )
    return result.embeddings[0].values


def _embed_batch_with_retry(texts: list[str]) -> list[list[float]]:
    """Embed a single batch with retry on rate-limit errors."""
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
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                wait_time = min(62 + 30 * attempt, 120)
                print(f"   ⏳ Rate limited (attempt {attempt + 1}/{_RATE_LIMIT_MAX_RETRIES}). "
                      f"Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise

    raise RuntimeError(
        f"Embedding failed after {_RATE_LIMIT_MAX_RETRIES} retries. "
        f"You've likely hit the DAILY quota (1,000 requests/day on free tier). "
        f"Wait until tomorrow, or set up billing at https://aistudio.google.com "
        f"for higher limits."
    )


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Batch embed texts with rate-limit awareness for free tier."""
    total = len(texts)
    all_embeddings: list[list[float]] = []
    total_batches = (total + _EMBED_BATCH_LIMIT - 1) // _EMBED_BATCH_LIMIT

    print(f"   📊 Total: {total} chunks → {total_batches} batch(es) of ≤{_EMBED_BATCH_LIMIT}")

    # Warn about daily quota usage
    print(f"   💡 Daily quota usage: ~{total} of 1,000 RPD (free tier)")
    if total > 800:
        print(f"   ⚠️  WARNING: This will use {total}/1000 of your daily quota!")

    if total_batches > 1:
        est_minutes = (total_batches - 1) * _BATCH_DELAY_SECONDS / 60
        print(f"   ⏱️  Estimated time: ~{est_minutes:.0f} min")

    for batch_num, i in enumerate(range(0, total, _EMBED_BATCH_LIMIT), 1):
        batch = texts[i : i + _EMBED_BATCH_LIMIT]

        print(f"   📦 Batch {batch_num}/{total_batches} ({len(batch)} chunks)...")

        embeddings = _embed_batch_with_retry(batch)
        all_embeddings.extend(embeddings)

        if batch_num < total_batches:
            remaining = total_batches - batch_num
            print(f"   ⏳ Waiting {_BATCH_DELAY_SECONDS}s for quota reset "
                  f"({remaining} batch(es) left)...")
            time.sleep(_BATCH_DELAY_SECONDS)

    print(f"   ✅ All {total} chunks embedded successfully!")
    return all_embeddings


# ──────────────────────────────────────────────
# Collection Management
# ──────────────────────────────────────────────

def _collection_name(company: str) -> str:
    """Sanitize company name into a valid ChromaDB collection name."""
    name = company.lower().strip()
    name = name.replace(" ", "-").replace("&", "and")
    name = "".join(c for c in name if c.isalnum() or c in "._-")
    name = name.strip("._-")
    if len(name) < 3:
        name = "co-" + name if name else "company"
    return name[:63]


def get_or_create_collection(company: str) -> chromadb.Collection:
    chroma = _get_chroma()
    return chroma.get_or_create_collection(
        name=_collection_name(company),
        metadata={"hnsw:space": "cosine"},
    )


def delete_collection(company: str) -> None:
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


def store_chunks(company: str, chunks: list[dict]) -> int:
    """Embed and store document chunks in ChromaDB."""
    collection = get_or_create_collection(company)

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

        meta = {}
        for k, v in chunk.get("metadata", {}).items():
            if isinstance(v, list):
                meta[k] = ",".join(str(x) for x in v)
            else:
                meta[k] = v
        all_metadatas.append(meta)

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
    if n_results is None:
        n_results = settings.retrieval_top_k

    collection = get_or_create_collection(company)

    if collection.count() == 0:
        return []

    query_embedding = get_embedding(query)

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