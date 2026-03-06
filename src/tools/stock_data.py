"""
Stock data tool — fetches live market data from yfinance.
Supports NSE (.NS) and BSE (.BO) tickers.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta

import yfinance as yf

from src.config.settings import settings
from src.models.schemas import MarketData, StockPrice, StockFundamentals, Exchange


# ──────────────────────────────────────────────
# Ticker Resolution
# ──────────────────────────────────────────────

# Common Indian stock ticker mappings (expand as needed)
TICKER_MAP: dict[str, str] = {
    "reliance": "RELIANCE.NS",
    "reliance industries": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "tata consultancy": "TCS.NS",
    "infosys": "INFY.NS",
    "hdfc bank": "HDFCBANK.NS",
    "icici bank": "ICICIBANK.NS",
    "sbi": "SBIN.NS",
    "wipro": "WIPRO.NS",
    "hul": "HINDUNILVR.NS",
    "hindustan unilever": "HINDUNILVR.NS",
    "bharti airtel": "BHARTIARTL.NS",
    "airtel": "BHARTIARTL.NS",
    "itc": "ITC.NS",
    "asian paints": "ASIANPAINT.NS",
    "kotak bank": "KOTAKBANK.NS",
    "kotak mahindra": "KOTAKBANK.NS",
    "maruti": "MARUTI.NS",
    "maruti suzuki": "MARUTI.NS",
    "bajaj finance": "BAJFINANCE.NS",
    "tatamotors": "TATAMOTORS.NS",
    "tata motors": "TATAMOTORS.NS",
    "tata steel": "TATASTEEL.NS",
    "adani enterprises": "ADANIENT.NS",
    "adani ports": "ADANIPORTS.NS",
    "power grid": "POWERGRID.NS",
    "ntpc": "NTPC.NS",
    "sun pharma": "SUNPHARMA.NS",
    "axis bank": "AXISBANK.NS",
    "lt": "LT.NS",
    "larsen": "LT.NS",
    "larsen & toubro": "LT.NS",
    "hcl tech": "HCLTECH.NS",
    "hcltech": "HCLTECH.NS",
    "tech mahindra": "TECHM.NS",
}


def resolve_ticker(company_name: str, exchange: Exchange = Exchange.NSE) -> str:
    """
    Resolve a company name to its yfinance ticker symbol.
    Falls back to appending .NS/.BO suffix if not found in map.
    """
    name_lower = company_name.strip().lower()

    # Check exact match in map
    if name_lower in TICKER_MAP:
        ticker = TICKER_MAP[name_lower]
        if exchange == Exchange.BSE:
            ticker = ticker.replace(".NS", ".BO")
        return ticker

    # Fallback: assume the input is already a ticker symbol
    suffix = ".NS" if exchange == Exchange.NSE else ".BO"
    clean = company_name.strip().upper().replace(" ", "")
    if not clean.endswith((".NS", ".BO")):
        clean += suffix
    return clean


# ──────────────────────────────────────────────
# Cache Helpers
# ──────────────────────────────────────────────

def _cache_path(ticker: str) -> Path:
    safe_name = ticker.replace(".", "_")
    return Path(settings.cache_dir) / "market_data" / f"{safe_name}.json"


def _read_cache(ticker: str) -> dict | None:
    path = _cache_path(ticker)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    cached_at = datetime.fromisoformat(data.get("_cached_at", "2000-01-01"))
    if datetime.now() - cached_at > timedelta(hours=settings.market_data_cache_hours):
        return None  # stale
    return data


def _write_cache(ticker: str, data: dict) -> None:
    path = _cache_path(ticker)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["_cached_at"] = datetime.now().isoformat()
    path.write_text(json.dumps(data, default=str))


# ──────────────────────────────────────────────
# Main Fetch Function
# ──────────────────────────────────────────────

def fetch_stock_data(company_name: str, exchange: Exchange = Exchange.NSE) -> MarketData:
    """
    Fetch current stock price + fundamentals for an Indian stock.

    Args:
        company_name: Company name or ticker (e.g., "Reliance" or "RELIANCE.NS")
        exchange: NSE or BSE

    Returns:
        MarketData model with price, fundamentals, and basic info.
    """
    ticker_symbol = resolve_ticker(company_name, exchange)

    # Check cache first
    cached = _read_cache(ticker_symbol)
    if cached and "_cached_at" in cached:
        cached.pop("_cached_at")
        return MarketData(**cached)

    # Fetch from yfinance
    stock = yf.Ticker(ticker_symbol)
    info = stock.info

    # Build price data
    price = StockPrice(
        current_price=info.get("currentPrice", info.get("regularMarketPrice", 0)),
        open_price=info.get("open", info.get("regularMarketOpen", 0)),
        day_high=info.get("dayHigh", info.get("regularMarketDayHigh", 0)),
        day_low=info.get("dayLow", info.get("regularMarketDayLow", 0)),
        week_52_high=info.get("fiftyTwoWeekHigh", 0),
        week_52_low=info.get("fiftyTwoWeekLow", 0),
        volume=info.get("volume", info.get("regularMarketVolume", 0)),
    )

    # Build fundamentals
    fundamentals = StockFundamentals(
        market_cap=round(info.get("marketCap", 0) / 1e7, 2),  # convert to crore
        pe_ratio=info.get("trailingPE", info.get("forwardPE", 0)) or 0,
        pb_ratio=info.get("priceToBook", 0) or 0,
        eps=info.get("trailingEps", 0) or 0,
        dividend_yield=round((info.get("dividendYield", 0) or 0) * 100, 2),
        roe=round((info.get("returnOnEquity", 0) or 0) * 100, 2),
        debt_to_equity=info.get("debtToEquity", 0) or 0,
        book_value=info.get("bookValue", 0) or 0,
        face_value=info.get("faceValue", 0) or 0,
        sector=info.get("sector", ""),
        industry=info.get("industry", ""),
    )

    market_data = MarketData(
        company_name=info.get("longName", company_name),
        ticker=ticker_symbol,
        exchange=exchange,
        price=price,
        fundamentals=fundamentals,
    )

    # Cache it
    _write_cache(ticker_symbol, market_data.model_dump())

    return market_data


# ──────────────────────────────────────────────
# ADK Tool Wrapper
# ──────────────────────────────────────────────

def get_stock_data(company_name: str, exchange: str = "NSE") -> dict:
    """
    ADK-compatible tool function.
    Fetches stock price and fundamentals for an Indian listed company.

    Args:
        company_name: Name of the company (e.g., "Reliance Industries")
        exchange: "NSE" or "BSE" (default: NSE)

    Returns:
        Dictionary with current price, fundamentals, and company info.
    """
    ex = Exchange.BSE if exchange.upper() == "BSE" else Exchange.NSE
    data = fetch_stock_data(company_name, ex)
    return data.model_dump()
