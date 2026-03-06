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
        - RECOMMENDATION must be BUY, SELL, or HOLD.
        - BUY only if the company has strong fundamentals AND a fair price.
        - SELL if the company has deteriorating fundamentals or extreme valuation.
        - RISK SCORE: 1 (Safe) to 10 (Speculative).
        """

        user_prompt = f"""
        Company: {market_data.company_name}
        Current Price: {market_data.price.current_price}
        
        --- FINANCIAL HEALTH (Score: {score}/10) ---
        Strengths: {", ".join(analysis_report.strengths)}
        Weaknesses: {", ".join(analysis_report.weaknesses)}
        Debt Analysis: {analysis_report.debt_analysis}
        
        --- TASK ---
        Provide a final investment recommendation in JSON format containing:
        verdict, time_horizon, risk_score, suggested_entry_price, bull_case, bear_case, reasoning.
        """

        response = self.client.models.generate_content(
            model=settings.gemini_model,
            contents=user_prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=0.4 # Slightly higher creativity for reasoning
            )
        )

        try:
            data = json.loads(response.text)
            
            return Recommendation(
                company_name=market_data.company_name,
                verdict=data.get("verdict", "HOLD"),
                time_horizon=data.get("time_horizon", "LONG_TERM"),
                risk_score=data.get("risk_score", 5),
                suggested_entry_price=data.get("suggested_entry_price", market_data.price.current_price),
                bull_case=data.get("bull_case", ""),
                bear_case=data.get("bear_case", ""),
                reasoning=data.get("reasoning", ""),
                key_catalysts=data.get("key_catalysts", [])
            )
        except Exception as e:
            print(f"❌ [Advisor Agent] Error: {e}")
            return Recommendation(company_name=market_data.company_name)