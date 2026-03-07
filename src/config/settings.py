"""
Application settings — loaded from .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration in one place. Values come from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Gemini (LLM + Embeddings) ---
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "gemini-embedding-001"
    llm_temperature: float = 0.2

    # --- Tavily (Web Search) ---
    tavily_api_key: str = ""

    # --- RAG Settings ---
    # chunk_size=2000 keeps total chunks under ~400 for a 150-page PDF
    # This is critical for free tier (1,000 RPD limit)
    chunk_size: int = 2000
    chunk_overlap: int = 200
    retrieval_top_k: int = 8

    # --- ChromaDB ---
    chroma_db_path: str = "data/cache/chroma_db"

    # --- Cache ---
    cache_dir: str = "data/cache"
    market_data_cache_hours: int = 24
    search_cache_hours: int = 168  # 7 days

    # --- App ---
    app_name: str = "Stock Analysis Agent"
    debug: bool = False


# Singleton — import this everywhere
settings = Settings()