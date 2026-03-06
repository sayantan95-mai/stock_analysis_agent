"""
Analysis Agent — performs fundamental analysis and generates a scorecard.
"""
import json
from google import genai
from src.config.settings import settings
from src.models.schemas import MarketData, AnalysisReport, ScoreCard


class AnalysisAgent:
    def __init__(self):
        self.client = genai.Client(api_key=settings.google_api_key)

    def analyze(self, market_data: MarketData, document_summaries: str) -> AnalysisReport:
        print(f"📊 [Analysis Agent] Crunching numbers for {market_data.company_name}...")

        system_prompt = """
        You are a strict financial auditor. Your job is to analyze the provided financial data
        and generate a structured 'Financial Health Scorecard' (0-10) for the company.

        Scoring Criteria:
        - 8-10: Exceptional (Industry leader, strong trends)
        - 5-7:  Average (Stable but not outstanding)
        - 2-4:  Weak (Declining metrics, concerns)
        - 0-1:  Dangerous (Severe issues)

        You MUST respond with ONLY a valid JSON object. No markdown, no explanation outside JSON.
        """

        # Prompt with FLAT keys matching the parsing code exactly
        user_prompt = f"""
        Analyze this company: {market_data.company_name}

        --- MARKET DATA ---
        Price: ₹{market_data.price.current_price}
        P/E Ratio: {market_data.fundamentals.pe_ratio}
        P/B Ratio: {market_data.fundamentals.pb_ratio}
        D/E Ratio: {market_data.fundamentals.debt_to_equity}
        ROE: {market_data.fundamentals.roe}%
        EPS: ₹{market_data.fundamentals.eps}
        Market Cap: ₹{market_data.fundamentals.market_cap} Cr
        Sector: {market_data.fundamentals.sector}
        News Sentiment: {market_data.news_sentiment_summary}

        --- DOCUMENT INSIGHTS (RAG) ---
        {document_summaries}

        --- TASK ---
        Return a JSON object with these EXACT top-level keys:

        {{
            "score_card": {{
                "revenue_growth": <int 0-10>,
                "profit_margin": <int 0-10>,
                "debt_health": <int 0-10>,
                "cash_flow": <int 0-10>,
                "return_ratios": <int 0-10>,
                "earnings_consistency": <int 0-10>
            }},
            "revenue_trend": "<2-3 sentence summary of revenue trend>",
            "profit_trend": "<2-3 sentence summary of profit trend>",
            "debt_analysis": "<2-3 sentence summary of debt health>",
            "strengths": ["strength 1", "strength 2", "strength 3"],
            "weaknesses": ["weakness 1", "weakness 2", "weakness 3"]
        }}
        """

        try:
            response = self.client.models.generate_content(
                model=settings.gemini_model,
                contents=user_prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )

            data = json.loads(response.text)

            # Create ScoreCard with validation
            score_card = ScoreCard(**data.get("score_card", {}))
            score_card.calculate_overall()

            report = AnalysisReport(
                company_name=market_data.company_name,
                score_card=score_card,
                revenue_trend=data.get("revenue_trend", "Data not available"),
                profit_trend=data.get("profit_trend", "Data not available"),
                debt_analysis=data.get("debt_analysis", "Data not available"),
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
            )
            return report

        except json.JSONDecodeError as e:
            print(f"❌ [Analysis Agent] JSON parse error: {e}")
            print(f"   Raw response: {response.text[:200]}")
            return AnalysisReport(company_name=market_data.company_name)
        except Exception as e:
            print(f"❌ [Analysis Agent] Error: {e}")
            return AnalysisReport(company_name=market_data.company_name)
