"""
Research Agent — gathers live market data and news.
"""
from google import genai
from src.config.settings import settings
from src.tools.stock_data import get_stock_data
from src.tools.web_search import search_company_news
from src.models.schemas import MarketData, NewsItem


class ResearchAgent:
    def __init__(self):
        self.client = genai.Client(api_key=settings.google_api_key)

    def analyze(self, company_name: str) -> MarketData:
        print(f"🔍 [Research Agent] Starting analysis for: {company_name}...")

        # 1. Fetch Hard Data (Stock Price & Fundamentals)
        print(f"   ... Fetching market data from yfinance")
        stock_raw = get_stock_data(company_name)

        # 2. Fetch Soft Data (News)
        print(f"   ... Searching news via Tavily/DuckDuckGo")
        try:
            news_raw = search_company_news(company_name, max_results=5)
        except Exception as e:
            print(f"   ⚠️ News search failed: {e}")
            news_raw = []

        # Convert raw news to Pydantic models
        news_items = [
            NewsItem(
                title=n["title"],
                snippet=n["snippet"],
                url=n["url"],
                date=n.get("date", ""),
            )
            for n in news_raw
        ]

        # 3. AI Synthesis: Generate Sentiment Summary
        print(f"   ... Analyzing news sentiment with Gemini")
        sentiment_summary = self._summarize_news_sentiment(company_name, news_items)

        # 4. Construct Final MarketData Object
        market_data = MarketData(
            company_name=stock_raw["company_name"],
            ticker=stock_raw["ticker"],
            exchange=stock_raw["exchange"],
            price=stock_raw["price"],
            fundamentals=stock_raw["fundamentals"],
            news=news_items,
            news_sentiment_summary=sentiment_summary,
        )

        print(f"   ✅ Research complete: {market_data.ticker} @ ₹{market_data.price.current_price}")
        return market_data

    def _summarize_news_sentiment(self, company: str, news: list[NewsItem]) -> str:
        """Uses LLM to generate a short sentiment summary from news headlines."""
        if not news:
            return "No recent news found to analyze sentiment."

        news_text = "\n".join([f"- {n.title}: {n.snippet}" for n in news])

        prompt = f"""
        You are a financial analyst. Analyze the following recent news for {company}:

        {news_text}

        Output a concise 2-sentence summary of the current market sentiment 
        (Bullish/Bearish/Neutral) and the key reason why.
        """

        try:
            response = self.client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            print(f"   ⚠️ Sentiment analysis failed: {e}")
            return "Sentiment analysis unavailable."
