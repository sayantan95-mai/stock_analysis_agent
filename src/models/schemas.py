"""
Pydantic models — shared data contracts between agents.
"""

from pydantic import BaseModel, Field
from enum import Enum


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class Verdict(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TimeHorizon(str, Enum):
    SHORT_TERM = "SHORT_TERM"   # < 6 months
    LONG_TERM = "LONG_TERM"     # > 1 year


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"


# ──────────────────────────────────────────────
# Research Agent Models
# ──────────────────────────────────────────────

class StockPrice(BaseModel):
    current_price: float = 0.0
    open_price: float = 0.0
    day_high: float = 0.0
    day_low: float = 0.0
    week_52_high: float = 0.0
    week_52_low: float = 0.0
    volume: int = 0


class StockFundamentals(BaseModel):
    market_cap: float = 0.0          # in crore
    pe_ratio: float = 0.0
    pb_ratio: float = 0.0
    eps: float = 0.0
    dividend_yield: float = 0.0
    roe: float = 0.0
    roce: float = 0.0
    debt_to_equity: float = 0.0
    book_value: float = 0.0
    face_value: float = 0.0
    sector: str = ""
    industry: str = ""


class NewsItem(BaseModel):
    title: str
    snippet: str = ""
    url: str = ""
    date: str = ""
    sentiment: str = "neutral"  # positive / negative / neutral


class MarketData(BaseModel):
    """Complete output of the Research Agent."""
    company_name: str
    ticker: str
    exchange: Exchange = Exchange.NSE
    price: StockPrice = Field(default_factory=StockPrice)
    fundamentals: StockFundamentals = Field(default_factory=StockFundamentals)
    news: list[NewsItem] = Field(default_factory=list)
    news_sentiment_summary: str = ""


# ──────────────────────────────────────────────
# Document Agent Models
# ──────────────────────────────────────────────

class DocumentChunk(BaseModel):
    content: str
    page: int = 0
    content_type: str = "text"   # "text" or "table"
    sections: list[str] = Field(default_factory=list)
    doc_type: str = ""           # annual_report, quarterly, etc.
    period: str = ""             # FY2024, Q3_FY2024, etc.


class DocumentSummary(BaseModel):
    """Summary produced after ingesting a document."""
    filename: str
    doc_type: str
    period: str
    total_chunks: int = 0
    key_metrics_found: list[str] = Field(default_factory=list)


# ──────────────────────────────────────────────
# Analysis Agent Models
# ──────────────────────────────────────────────

class ScoreCard(BaseModel):
    """Financial health score — each metric scored 1-10."""
    revenue_growth: int = Field(0, ge=0, le=10)
    profit_margin: int = Field(0, ge=0, le=10)
    debt_health: int = Field(0, ge=0, le=10)
    cash_flow: int = Field(0, ge=0, le=10)
    return_ratios: int = Field(0, ge=0, le=10)
    earnings_consistency: int = Field(0, ge=0, le=10)
    overall_score: float = 0.0   # weighted average

    def calculate_overall(self) -> float:
        scores = [
            self.revenue_growth,
            self.profit_margin,
            self.debt_health,
            self.cash_flow,
            self.return_ratios,
            self.earnings_consistency,
        ]
        self.overall_score = round(sum(scores) / len(scores), 1)
        return self.overall_score


class AnalysisReport(BaseModel):
    """Output of the Analysis Agent."""
    company_name: str
    score_card: ScoreCard = Field(default_factory=ScoreCard)
    revenue_trend: str = ""
    profit_trend: str = ""
    debt_analysis: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM


# ──────────────────────────────────────────────
# Advisor Agent Models
# ──────────────────────────────────────────────

class Recommendation(BaseModel):
    """Final output — the investment recommendation."""
    company_name: str
    verdict: Verdict = Verdict.HOLD
    time_horizon: TimeHorizon = TimeHorizon.LONG_TERM
    risk_score: int = Field(5, ge=1, le=10)   # 1=safe, 10=risky
    suggested_entry_price: float = 0.0
    bull_case: str = ""
    bear_case: str = ""
    key_catalysts: list[str] = Field(default_factory=list)
    reasoning: str = ""
    confidence: Confidence = Confidence.MEDIUM
    disclaimer: str = (
        "This is for educational and informational purposes only. "
        "It does not constitute financial advice. Always consult a "
        "qualified financial advisor before making investment decisions."
    )
