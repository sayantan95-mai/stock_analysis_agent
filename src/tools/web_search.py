"""
Web search tool — Tavily (primary) + DuckDuckGo (free fallback).
Used by Research Agent for company news and context.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from hashlib import md5

from src.config.settings import settings
from src.models.schemas import NewsItem


# ──────────────────────────────────────────────
# Cache Helpers
# ──────────────────────────────────────────────

def _cache_key(query: str) -> str:
    return md5(query.encode()).hexdigest()


def _cache_path(query: str) -> Path:
    return Path(settings.cache_dir) / "search_results" / f"{_cache_key(query)}.json"


def _read_cache(query: str) -> list[dict] | None:
    path = _cache_path(query)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    cached_at = datetime.fromisoformat(data.get("_cached_at", "2000-01-01"))
    if datetime.now() - cached_at > timedelta(hours=settings.search_cache_hours):
        return None
    return data.get("results", [])


def _write_cache(query: str, results: list[dict]) -> None:
    path = _cache_path(query)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"_cached_at": datetime.now().isoformat(), "results": results}
    path.write_text(json.dumps(payload, default=str))


# ──────────────────────────────────────────────
# Tavily Search (Primary)
# ──────────────────────────────────────────────

def _search_tavily(query: str, max_results: int = 5) -> list[dict]:
    """Search using Tavily API (1000 free searches/month)."""
    from tavily import TavilyClient

    if not settings.tavily_api_key:
        raise ValueError("TAVILY_API_KEY not set in .env")

    client = TavilyClient(api_key=settings.tavily_api_key)
    response = client.search(
        query=query,
        max_results=max_results,
        search_depth="basic",
        include_answer=True,
    )

    results = []
    for item in response.get("results", []):
        results.append({
            "title": item.get("title", ""),
            "snippet": item.get("content", ""),
            "url": item.get("url", ""),
            "date": item.get("published_date", ""),
        })
    return results


# ──────────────────────────────────────────────
# DuckDuckGo Search (Free Fallback)
# ──────────────────────────────────────────────

def _search_duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    """Search using DuckDuckGo — completely free, no API key."""
    try:
        from ddgs import DDGS  # new package name
    except ImportError:
        from duckduckgo_search import DDGS  # legacy fallback

    results = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=max_results):
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("body", ""),
                "url": item.get("href", ""),
                "date": item.get("date", ""),
            })
    return results


# ──────────────────────────────────────────────
# Unified Search Function
# ──────────────────────────────────────────────

def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web. Tries Tavily first, falls back to DuckDuckGo.

    Args:
        query: Search query string.
        max_results: Max number of results.

    Returns:
        List of dicts with title, snippet, url, date.
    """
    # Check cache
    cached = _read_cache(query)
    if cached is not None:
        return cached[:max_results]

    results = []

    # Try Tavily first
    if settings.tavily_api_key:
        try:
            results = _search_tavily(query, max_results)
        except Exception as e:
            print(f"[search] Tavily failed: {e}, falling back to DuckDuckGo")

    # Fallback to DuckDuckGo
    if not results:
        try:
            results = _search_duckduckgo(query, max_results)
        except Exception as e:
            print(f"[search] DuckDuckGo also failed: {e}")

    # Cache results
    if results:
        _write_cache(query, results)

    return results


# ──────────────────────────────────────────────
# ADK Tool Wrapper
# ──────────────────────────────────────────────

def search_company_news(company_name: str, max_results: int = 5) -> list[dict]:
    """
    ADK-compatible tool function.
    Search for recent news and information about a company.

    Args:
        company_name: Name of the company (e.g., "Reliance Industries")
        max_results: Number of results to return (default: 5)

    Returns:
        List of news items with title, snippet, url, and date.
    """
    query = f"{company_name} stock market news India latest"
    return search_web(query, max_results)


def search_stock_analysis(company_name: str, topic: str = "financial performance") -> list[dict]:
    """
    ADK-compatible tool function.
    Search for specific stock analysis topics.

    Args:
        company_name: Name of the company
        topic: What to search for (e.g., "quarterly results", "debt analysis")

    Returns:
        List of search results.
    """
    query = f"{company_name} {topic} India stock analysis"
    return search_web(query, max_results=5)
