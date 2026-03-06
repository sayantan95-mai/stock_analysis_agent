"""
Streamlit UI for the Stock Analysis Multi-Agent System.

Run: uv run streamlit run src/ui/app.py
"""
import sys
from pathlib import Path

# ── Fix: Add project root to sys.path so 'src' imports work ──
# Streamlit runs scripts from the file's directory, not the project root
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st

# Fix for async loop errors in some environments
import asyncio
try:
    asyncio.get_running_loop()
except RuntimeError:
    pass

from src.agents.orchestrator import OrchestratorAgent

# ──────────────────────────────────────────────
# Page Config
# ──────────────────────────────────────────────
st.set_page_config(page_title="AI Stock Analyst", page_icon="📈", layout="wide")


# ──────────────────────────────────────────────
# Session State Initialization
# ──────────────────────────────────────────────
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None
if "results" not in st.session_state:
    st.session_state.results = None
if "company_name" not in st.session_state:
    st.session_state.company_name = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def save_uploaded_file(uploaded_file) -> str:
    """Save uploaded PDF to disk and return path."""
    save_dir = Path("data/uploads")
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(file_path)


def safe_progress(score: int) -> float:
    """Safely convert score (0-10) to progress value (0.0-1.0)."""
    if score is None or score <= 0:
        return 0.01
    return min(score / 10, 1.0)


# ──────────────────────────────────────────────
# Sidebar: Inputs
# ──────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")
    company_name = st.text_input("Company Name", "Reliance Industries")

    uploaded_files = st.file_uploader(
        "Upload Annual Reports (PDF)",
        type="pdf",
        accept_multiple_files=True,
    )

    start_btn = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    if st.session_state.results:
        st.divider()
        st.caption(f"Last analysis: **{st.session_state.company_name}**")
        if st.button("🗑️ Clear Results"):
            st.session_state.results = None
            st.session_state.orchestrator = None
            st.session_state.chat_history = []
            st.rerun()


# ──────────────────────────────────────────────
# Main Area
# ──────────────────────────────────────────────
st.title("📈 AI Financial Analyst Agent")
st.markdown("Your autonomous team for stock research, document analysis, and investment advice.")


# ──────────────────────────────────────────────
# Run Analysis
# ──────────────────────────────────────────────
if start_btn and company_name:
    orchestrator = OrchestratorAgent()
    st.session_state.orchestrator = orchestrator
    st.session_state.company_name = company_name
    st.session_state.chat_history = []

    pdf_paths = []
    if uploaded_files:
        with st.status("📂 Processing uploaded documents...", expanded=True):
            for file in uploaded_files:
                path = save_uploaded_file(file)
                pdf_paths.append(path)
                st.write(f"✅ Saved {file.name}")

    try:
        with st.status("🤖 AI Agents at work...", expanded=True) as status:
            st.write("🔍 Research Agent: Fetching market data & news...")
            results = orchestrator.run_analysis(company_name, pdf_paths)
            status.update(label="✅ Analysis Complete!", state="complete", expanded=False)

        st.session_state.results = results

    except Exception as e:
        st.error(f"❌ Analysis failed: {e}")
        st.info("Check your API keys in `.env` and try again.")
        st.stop()


# ──────────────────────────────────────────────
# Display Results (from session state)
# ──────────────────────────────────────────────
if st.session_state.results:
    results = st.session_state.results
    rec = results["recommendation"]
    data = results["market_data"]
    report = results["analysis_report"]

    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])

    color_map = {"BUY": "green", "SELL": "red", "HOLD": "orange"}
    verdict_str = rec.verdict.value if hasattr(rec.verdict, "value") else str(rec.verdict)
    color = color_map.get(verdict_str, "blue")

    with col1:
        st.markdown(f"## Verdict: :{color}[{verdict_str}]")
    with col2:
        st.metric("Target Entry Price", f"₹{rec.suggested_entry_price:,.2f}")
    with col3:
        st.metric("Risk Score", f"{rec.risk_score}/10")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Financial Health",
        "📰 Market Research",
        "💡 Deep Dive",
        "💬 Chat with Data",
    ])

    with tab1:
        st.subheader("Financial Health Scorecard")
        score = report.score_card

        overall = score.overall_score or score.calculate_overall()
        st.metric("Overall Score", f"{overall}/10")

        c1, c2 = st.columns(2)
        with c1:
            st.write("**Revenue Growth**")
            st.progress(safe_progress(score.revenue_growth), text=f"{score.revenue_growth}/10")
            st.write("**Profit Margins**")
            st.progress(safe_progress(score.profit_margin), text=f"{score.profit_margin}/10")
            st.write("**Cash Flow**")
            st.progress(safe_progress(score.cash_flow), text=f"{score.cash_flow}/10")
        with c2:
            st.write("**Debt Health**")
            st.progress(safe_progress(score.debt_health), text=f"{score.debt_health}/10")
            st.write("**ROE / ROCE**")
            st.progress(safe_progress(score.return_ratios), text=f"{score.return_ratios}/10")
            st.write("**Earnings Consistency**")
            st.progress(safe_progress(score.earnings_consistency), text=f"{score.earnings_consistency}/10")

        st.info(f"**Analyst Note:** {report.revenue_trend}")
        if report.debt_analysis:
            st.info(f"**Debt Analysis:** {report.debt_analysis}")

        s1, s2 = st.columns(2)
        with s1:
            st.subheader("💪 Strengths")
            for s in report.strengths:
                st.markdown(f"- {s}")
        with s2:
            st.subheader("⚠️ Weaknesses")
            for w in report.weaknesses:
                st.markdown(f"- {w}")

    with tab2:
        st.subheader("Live Market Data")
        m = data.fundamentals
        p = data.price

        pc1, pc2, pc3 = st.columns(3)
        pc1.metric("Current Price", f"₹{p.current_price:,.2f}")
        pc2.metric("Day Range", f"₹{p.day_low:,.0f} - ₹{p.day_high:,.0f}")
        pc3.metric("52-Week Range", f"₹{p.week_52_low:,.0f} - ₹{p.week_52_high:,.0f}")

        rm1, rm2, rm3, rm4 = st.columns(4)
        rm1.metric("P/E Ratio", f"{m.pe_ratio:.1f}")
        rm2.metric("Market Cap", f"₹{m.market_cap:,.0f} Cr")
        rm3.metric("ROE", f"{m.roe:.1f}%")
        rm4.metric("Debt/Equity", f"{m.debt_to_equity:.2f}")

        st.subheader("News Sentiment")
        st.warning(data.news_sentiment_summary or "No sentiment data available")

        st.subheader("Recent Headlines")
        if data.news:
            for news in data.news:
                st.markdown(f"- [{news.title}]({news.url})")
        else:
            st.caption("No recent news found.")

    with tab3:
        st.subheader("Investment Thesis")
        if rec.bull_case:
            st.success(f"**Bull Case:** {rec.bull_case}")
        if rec.bear_case:
            st.error(f"**Bear Case:** {rec.bear_case}")

        if rec.key_catalysts:
            st.subheader("🚀 Key Catalysts")
            for catalyst in rec.key_catalysts:
                st.markdown(f"- {catalyst}")

        st.markdown("### 📝 Detailed Reasoning")
        st.write(rec.reasoning or "No detailed reasoning provided.")

    with tab4:
        st.subheader("Ask the Document Agent")

        if not st.session_state.orchestrator or not st.session_state.orchestrator.document_agent.has_documents(
            st.session_state.company_name
        ):
            st.info("📤 Upload annual reports in the sidebar to enable document Q&A.")
        else:
            st.markdown("Ask specific questions about the uploaded annual reports.")

            for entry in st.session_state.chat_history:
                with st.chat_message("user"):
                    st.write(entry["question"])
                with st.chat_message("assistant"):
                    st.write(entry["answer"])

            user_query = st.chat_input("Ask about the reports...")
            if user_query:
                with st.chat_message("user"):
                    st.write(user_query)

                with st.chat_message("assistant"):
                    with st.spinner("Searching documents..."):
                        answer = st.session_state.orchestrator.document_agent.ask(
                            st.session_state.company_name, user_query
                        )
                        st.write(answer)

                st.session_state.chat_history.append({
                    "question": user_query,
                    "answer": answer,
                })

    st.divider()
    st.caption(
        "⚠️ **Disclaimer:** This tool is for educational and informational purposes only. "
        "It does not constitute financial advice. Always consult a qualified financial "
        "advisor before making investment decisions."
    )

else:
    st.info("👈 Enter a company name and click **Run Analysis** to get started.")
    st.markdown(
        """
        **What this tool does:**
        1. 🔍 Fetches live stock data and recent news
        2. 📄 Analyses uploaded financial reports (optional)
        3. 📊 Generates a financial health scorecard
        4. 💡 Provides a Buy/Sell/Hold recommendation
        """
    )