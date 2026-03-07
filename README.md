# 📈 Stock Analysis Multi-Agent System

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Google%20ADK-Gemini-orange?style=for-the-badge&logo=google&logoColor=white" alt="Google ADK">
  <img src="https://img.shields.io/badge/Streamlit-UI-red?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/ChromaDB-Vector%20Store-green?style=for-the-badge" alt="ChromaDB">
</p>

<p align="center">
  <strong>An intelligent multi-agent system that analyzes stocks using real-time data, financial documents, and AI-powered insights to help you make informed investment decisions.</strong>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-tech-stack">Tech Stack</a>
</p>

---

## 🎯 What It Does

Simply enter a company name, upload financial documents (annual reports, quarterly filings), and get comprehensive investment analysis:

- **Buy / Sell / Hold** recommendations with confidence scores
- **Risk assessment** on a 1-10 scale
- **Short-term vs Long-term** investment outlook
- **Key catalysts and risks** to watch
- **Entry price suggestions** based on fundamental analysis

> *"Turn hours of financial research into minutes of actionable insights."*

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Real-Time Research** | Fetches current stock prices, P/E ratios, market cap, and recent news |
| 📄 **Document Intelligence** | Parses PDFs (annual reports, 10-K, earnings calls) with smart chunking |
| 📊 **Fundamental Analysis** | Analyzes revenue trends, profit margins, debt ratios, and growth metrics |
| 💡 **AI-Powered Advice** | Synthesizes all data into clear, actionable recommendations |
| 🧠 **RAG Pipeline** | Retrieval-Augmented Generation for accurate, document-grounded answers |
| 💬 **Conversational UI** | Ask follow-up questions naturally via Streamlit chat interface |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                           │
│                    (Streamlit Chat App)                         │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestrator Agent                          │
│          (Routes tasks, merges results, manages flow)           │
└─────────────────────────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ 🔍 Research     │  │ 📄 Document     │  │ 📊 Analysis     │
│    Agent        │  │    Agent        │  │    Agent        │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ • Web search    │  │ • PDF parsing   │  │ • Fundamentals  │
│ • Stock prices  │  │ • RAG retrieval │  │ • Trend analysis│
│ • News & events │  │ • Chunking      │  │ • Peer compare  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               ▼
                    ┌─────────────────┐
                    │ 💡 Advisor      │
                    │    Agent        │
                    ├─────────────────┤
                    │ • Buy/Sell/Hold │
                    │ • Risk score    │
                    │ • Entry price   │
                    └─────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Google AI API key ([Get one here](https://aistudio.google.com/apikey))

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/stock-analysis-agent.git
cd stock-analysis-agent

# Install dependencies with uv (recommended)
uv sync

# Or with pip
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### Run the App

```bash
uv run streamlit run src/ui/app.py
```

The app will open at `http://localhost:8501`

---

## 📖 Usage

### Basic Flow

1. **Enter Company Name** — Type any publicly traded company (e.g., "Apple", "Tesla", "Reliance Industries")

2. **Upload Documents** (Optional) — Drag and drop annual reports, quarterly filings, or earnings transcripts (PDF)

3. **Ask Questions** — Chat naturally:
   - *"Should I buy this stock for the long term?"*
   - *"What are the main risks?"*
   - *"Compare the last 4 quarters of revenue"*
   - *"What's the debt situation?"*

4. **Get Analysis** — Receive AI-powered insights grounded in real data and your documents

### Example Queries

```
💬 "Analyze Tata Motors for a 2-year investment horizon"
💬 "What does the annual report say about their EV strategy?"
💬 "Is the current P/E ratio justified given growth projections?"
💬 "Summarize key risks mentioned in the 10-K filing"
```

---

## ⚠️ Free Tier Rate Limits

This project works with Google's **free tier** Gemini API, which has the following limits:

| Resource | Limit | Impact |
|----------|-------|--------|
| **Gemini 2.5 Flash RPM** | 5 req/min | ~4 LLM calls per analysis run |
| **Gemini 2.5 Flash RPD** | 20 req/day | ~5 full analyses per day |
| **Embedding RPM** | 100 req/min | Batches of 25 with 62s delays |
| **Embedding TPM** | 30K tokens/min | Limits batch size to ~25 chunks |
| **Embedding RPD** | 1,000 req/day | ~300-400 chunks per PDF (1-2 large PDFs/day) |

**Tips for free tier:**
- Upload **one PDF at a time** (~300 chunks = 300 of 1,000 daily requests)
- A 150-page annual report takes **~10-12 minutes** to ingest
- Start without PDFs to test the basic analysis flow first
- Set up [billing](https://aistudio.google.com) for significantly higher limits

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|------------|
| **AI Framework** | Google ADK (Agent Development Kit) |
| **LLM** | Google Gemini 2.5 Flash |
| **Vector Database** | ChromaDB |
| **Embeddings** | Google Gemini Embedding 001 |
| **PDF Processing** | PyMuPDF (fitz) + pdfplumber |
| **Stock Data** | yfinance |
| **Web Search** | Tavily API + DuckDuckGo (fallback) |
| **UI** | Streamlit |
| **Package Manager** | uv |

---

## 📁 Project Structure

```
stock-analysis-agent/
├── src/
│   ├── agents/           # Multi-agent definitions
│   │   ├── orchestrator.py
│   │   ├── research_agent.py
│   │   ├── document_agent.py
│   │   ├── analysis_agent.py
│   │   └── advisor_agent.py
│   ├── rag/              # RAG pipeline components
│   │   ├── vector_store.py
│   │   └── pipeline.py
│   ├── tools/            # Agent tools
│   │   ├── stock_data.py
│   │   ├── web_search.py
│   │   └── pdf_parser.py
│   ├── models/
│   │   └── schemas.py    # Pydantic data models
│   ├── config/
│   │   └── settings.py   # App configuration
│   └── ui/
│       └── app.py        # Streamlit interface
├── data/
│   ├── uploads/          # Uploaded PDFs
│   └── cache/            # ChromaDB + search/market data cache
├── tests/
├── pyproject.toml
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Configuration

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here  # Optional: for web search
```

Key settings in `src/config/settings.py`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `gemini_model` | `gemini-2.5-flash` | LLM for analysis and advice |
| `embedding_model` | `gemini-embedding-001` | Embedding model for RAG |
| `chunk_size` | `2000` | Text chunk size (larger = fewer API calls) |
| `chunk_overlap` | `200` | Overlap between chunks |
| `retrieval_top_k` | `8` | Number of chunks retrieved per query |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 🤖 AI Assistance Acknowledgment

This project was developed with significant assistance from **Claude** (Anthropic's AI assistant). Claude contributed to:

- **Architecture Design** — System design, multi-agent orchestration patterns, and data flow planning
- **Code Implementation** — Python code for agents, RAG pipeline, vector store integration, and Streamlit UI
- **Debugging** — Identifying and resolving import issues, type hint compatibility, and runtime errors
- **Documentation** — This README and inline code documentation

> *This project demonstrates human-AI collaboration in software development. The core ideas, requirements, and project direction came from the developer, while Claude assisted with implementation details, best practices, and problem-solving.*

**Tools Used:**
- Claude (Anthropic) — Architecture, coding, debugging
- Google Gemini — Runtime LLM for stock analysis

---

## ⚠️ Disclaimer

This tool is for **educational and informational purposes only**. It does not constitute financial advice. Always:

- Do your own research before making investment decisions
- Consult with a qualified financial advisor
- Understand that stock investments carry risk of loss

The AI-generated recommendations are based on available data and should not be the sole basis for investment decisions.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>⭐ Star this repo if you find it useful!</strong>
</p>

<p align="center">
  Made with ❤️ and 🤖
</p>