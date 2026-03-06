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

        # 1. Construct the prompt with all available data
        system_prompt = """
        You are a strict financial auditor. Your job is to analyze the provided financial data 
        and generate a structured 'Financial Health Scorecard' (0-10) for the company.
        
        Scoring Criteria:
        - 10: Exceptional (Industry leader, perfect trends)
        - 5: Average (Stable but stagnant)
        - 1: Dangerous (Declining, high risk)
        
        Output MUST be valid JSON matching the schema provided.
        """

        user_prompt = f"""
        Analyze this company: {market_data.company_name}
        
        --- MARKET DATA ---
        Price: {market_data.price.current_price}
        P/E Ratio: {market_data.fundamentals.pe_ratio} (Sector Avg: ~25)
        D/E Ratio: {market_data.fundamentals.debt_to_equity}
        ROE: {market_data.fundamentals.roe}%
        News Sentiment: {market_data.news_sentiment_summary}
        
        --- DOCUMENT INSIGHTS (RAG) ---
        {document_summaries}
        
        --- TASK ---
        Generate a JSON object with:
        1. score_card: Scores (0-10) for revenue_growth, profit_margin, debt_health, cash_flow, return_ratios, earnings_consistency.
        2. analysis: Short text summary for revenue_trend, profit_trend, debt_analysis.
        3. lists: 3 key strengths and 3 key weaknesses.
        """

        # 2. Call Gemini with JSON enforcement
        response = self.client.models.generate_content(
            model=settings.gemini_model,
            contents=user_prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json", # Forces JSON output
                temperature=0.2
            )
        )

        # 3. Parse and Validate
        try:
            data = json.loads(response.text)
            
            # Create Pydantic models
            score_card = ScoreCard(**data.get("score_card", {}))
            score_card.calculate_overall() # Auto-calculate average
            
            report = AnalysisReport(
                company_name=market_data.company_name,
                score_card=score_card,
                revenue_trend=data.get("revenue_trend", "Data not available"),
                profit_trend=data.get("profit_trend", "Data not available"),
                debt_analysis=data.get("debt_analysis", "Data not available"),
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", [])
            )
            return report
            
        except Exception as e:
            print(f"❌ [Analysis Agent] Error parsing JSON: {e}")
            # Return empty report on failure to prevent crash
            return AnalysisReport(company_name=market_data.company_name)