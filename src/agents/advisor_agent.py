"""
Advisor Agent — synthesizes all data into a final recommendation.
"""
import json
from google import genai
from src.config.settings import settings
from src.models.schemas import AnalysisReport, Recommendation, MarketData


class AdvisorAgent:
    def __init__(self):
        self.client = genai.Client(api_key=settings.google_api_key)

    def advise(self, market_data: MarketData, analysis_report: AnalysisReport) -> Recommendation:
        print(f"💡 [Advisor Agent] Formulating final verdict for {market_data.company_name}...")

        score = analysis_report.score_card.overall_score

        system_prompt = """
        You are a conservative Investment Advisor (Warren Buffett style).
        Your goal is capital preservation first, growth second.

        Rules:
        - verdict MUST be exactly one of: "BUY", "SELL", or "HOLD" (uppercase).
        - time_horizon MUST be exactly: "SHORT_TERM" or "LONG_TERM".
        - risk_score: integer 1 (Safe) to 10 (Speculative).
        - suggested_entry_price: a realistic ₹ price based on current valuation.
        - BUY only if the company has strong fundamentals AND a fair price.
        - SELL if the company has deteriorating fundamentals or extreme valuation.
        - HOLD if fundamentals are decent but price is rich.

        You MUST respond with ONLY a valid JSON object.
        """

        user_prompt = f"""
        Company: {market_data.company_name}
        Ticker: {market_data.ticker}
        Current Price: ₹{market_data.price.current_price}
        52-Week Range: ₹{market_data.price.week_52_low} - ₹{market_data.price.week_52_high}
        P/E Ratio: {market_data.fundamentals.pe_ratio}
        Debt/Equity: {market_data.fundamentals.debt_to_equity}

        --- FINANCIAL HEALTH (Score: {score}/10) ---
        Revenue Growth: {analysis_report.score_card.revenue_growth}/10
        Profit Margin: {analysis_report.score_card.profit_margin}/10
        Debt Health: {analysis_report.score_card.debt_health}/10
        Cash Flow: {analysis_report.score_card.cash_flow}/10
        Strengths: {", ".join(analysis_report.strengths) or "None identified"}
        Weaknesses: {", ".join(analysis_report.weaknesses) or "None identified"}
        Debt Analysis: {analysis_report.debt_analysis}

        --- TASK ---
        Return a JSON object with these EXACT keys:
        {{
            "verdict": "BUY" | "SELL" | "HOLD",
            "time_horizon": "SHORT_TERM" | "LONG_TERM",
            "risk_score": <int 1-10>,
            "suggested_entry_price": <float>,
            "bull_case": "<2-3 sentences>",
            "bear_case": "<2-3 sentences>",
            "key_catalysts": ["catalyst 1", "catalyst 2", "catalyst 3"],
            "reasoning": "<3-5 sentence investment thesis>"
        }}
        """

        try:
            response = self.client.models.generate_content(
                model=settings.gemini_model,
                contents=user_prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.4,
                ),
            )

            data = json.loads(response.text)

            # Normalize verdict to uppercase for enum matching
            verdict = data.get("verdict", "HOLD").upper().strip()
            if verdict not in ("BUY", "SELL", "HOLD"):
                verdict = "HOLD"

            time_horizon = data.get("time_horizon", "LONG_TERM").upper().strip()
            if time_horizon not in ("SHORT_TERM", "LONG_TERM"):
                time_horizon = "LONG_TERM"

            return Recommendation(
                company_name=market_data.company_name,
                verdict=verdict,
                time_horizon=time_horizon,
                risk_score=max(1, min(10, int(data.get("risk_score", 5)))),
                suggested_entry_price=float(data.get("suggested_entry_price", market_data.price.current_price)),
                bull_case=data.get("bull_case", ""),
                bear_case=data.get("bear_case", ""),
                reasoning=data.get("reasoning", ""),
                key_catalysts=data.get("key_catalysts", []),
            )

        except json.JSONDecodeError as e:
            print(f"❌ [Advisor Agent] JSON parse error: {e}")
            print(f"   Raw response: {response.text[:200]}")
            return Recommendation(company_name=market_data.company_name)
        except Exception as e:
            print(f"❌ [Advisor Agent] Error: {e}")
            return Recommendation(company_name=market_data.company_name)
