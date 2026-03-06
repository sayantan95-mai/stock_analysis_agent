# 📊 Stock Analysis Multi-Agent System

An AI-powered stock analysis tool for **Indian markets (NSE/BSE)** built with Google ADK, Gemini, and a RAG pipeline.

## What It Does

Enter a company name → get a comprehensive investment analysis report with **Buy / Sell / Hold** recommendation.

**4 Specialist Agents:**
| Agent | Role |
|---|---|
| 🔍 Research Agent | Fetches live stock data + news via yfinance & Tavily |
| 📄 Document Agent | Parses annual reports & quarterly filings via RAG |
| 📊 Analysis Agent | Crunches numbers — trends, ratios, scorecard |
| 💡 Advisor Agent | Delivers verdict with risk assessment & reasoning |

## Quick Start

```bash
# 1. Clone and enter project
cd stock-analysis-agent

# 2. Copy env template and add your API keys
cp .env.example .env

# 3. Install dependencies
uv sync

# 4. Run (coming soon)
uv run streamlit run src/ui/app.py
```

## API Keys Needed (Free)

| Key | Where to Get | Free Tier |
|---|---|---|
| `GOOGLE_API_KEY` | [ai.google.dev](https://ai.google.dev/) | 1500 req/day |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com/) | 1000 searches/month |

## Tech Stack

- **Agent Framework:** Google ADK
- **LLM:** Gemini 2.0 Flash
- **Stock Data:** yfinance (NSE/BSE)
- **Web Search:** Tavily + DuckDuckGo
- **PDF Parsing:** pdfplumber + PyMuPDF
- **RAG:** ChromaDB + Gemini Embeddings
- **UI:** Streamlit

## Disclaimer

This tool is for **educational and informational purposes only**. It does not constitute financial advice.
