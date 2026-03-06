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

        VERDICT RULES (follow strictly):
        - verdict MUST be exactly one of: "BUY", "SELL", or "HOLD" (uppercase).
        - time_horizon MUST be exactly: "SHORT_TERM" or "LONG_TERM".
        - risk_score: integer 1 (Safe) to 10 (Speculative).
        - suggested_entry_price: a realistic ₹ price based on current valuation.

        DECISION CRITERIA:

        ✅ BUY only when ALL of these are true:
           - Overall score >= 7/10
           - Strong fundamentals (revenue growth + profit margins solid)
           - Reasonable valuation (P/E not excessively high vs sector)
           - Low to moderate debt (Debt/Equity < 1.0)
           - Clear growth catalysts identified

        🟡 HOLD when ANY of these are true:
           - Overall score is 4-6/10 (mixed signals)
           - Fundamentals are decent but valuation is stretched
           - Some strengths but also notable weaknesses
           - Uncertainty is high (awaiting earnings, regulatory clarity, etc.)
           - Stock is fairly valued (not cheap, not expensive)
           - Recent run-up in price — wait for pullback
           - Good company but not the right entry point

        ❌ SELL when ANY of these are true:
           - Overall score <= 3/10
           - Deteriorating fundamentals (declining revenue, shrinking margins)
           - Extreme overvaluation (P/E > 2x sector average)
           - High debt with weak cash flow (Debt/Equity > 2.0)
           - Significant red flags or governance concerns

        IMPORTANT: When in doubt, default to HOLD. It's better to wait than to 
        make a wrong BUY or SELL call. Most stocks should be HOLD.

        You MUST respond with ONLY a valid JSON object.
        """

        # Determine score zone for guidance
        if score >= 7:
            score_zone = "HIGH (7-10): Candidate for BUY if valuation is reasonable"
        elif score >= 4:
            score_zone = "MEDIUM (4-6): Default to HOLD — mixed signals"
        else:
            score_zone = "LOW (1-3): Consider SELL — weak fundamentals"

        user_prompt = f"""
        Company: {market_data.company_name}
        Ticker: {market_data.ticker}
        Current Price: ₹{market_data.price.current_price}
        52-Week Range: ₹{market_data.price.week_52_low} - ₹{market_data.price.week_52_high}
        P/E Ratio: {market_data.fundamentals.pe_ratio}
        Debt/Equity: {market_data.fundamentals.debt_to_equity}

        --- FINANCIAL HEALTH (Score: {score}/10) ---
        ⚡ SCORE ZONE: {score_zone}
        
        Revenue Growth: {analysis_report.score_card.revenue_growth}/10
        Profit Margin: {analysis_report.score_card.profit_margin}/10
        Debt Health: {analysis_report.score_card.debt_health}/10
        Cash Flow: {analysis_report.score_card.cash_flow}/10
        Strengths: {", ".join(analysis_report.strengths) or "None identified"}
        Weaknesses: {", ".join(analysis_report.weaknesses) or "None identified"}
        Debt Analysis: {analysis_report.debt_analysis}

        --- TASK ---
        Based on the SCORE ZONE and decision criteria, return a JSON object:
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