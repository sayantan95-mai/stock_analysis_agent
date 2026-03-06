from src.agents.research_agent import ResearchAgent
from dotenv import load_dotenv

# Load API keys
load_dotenv()

def main():
    agent = ResearchAgent()
    
    # Test with a real Indian company
    company = "Tata Motors"
    
    print(f"\n--- Testing Research Agent for {company} ---")
    data = agent.analyze(company)
    
    print(f"\n✅ Ticker: {data.ticker}")
    print(f"💰 Price: ₹{data.price.current_price}")
    print(f"📈 P/E Ratio: {data.fundamentals.pe_ratio}")
    print(f"📰 News Sentiment: {data.news_sentiment_summary}")
    
    print("\n✅ Research Agent Test Passed!")

if __name__ == "__main__":
    main()