import streamlit as st
import os
from pathlib import Path

# Fix for loop errors in some environments
import asyncio
try:
    asyncio.get_running_loop()
except RuntimeError:
    pass

from src.agents.orchestrator import OrchestratorAgent

# Page Config
st.set_page_config(page_title="AI Stock Analyst", page_icon="📈", layout="wide")

def save_uploaded_file(uploaded_file):
    """Helper to save uploaded PDF to disk."""
    save_dir = Path("data/uploads")
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(file_path)

# --- Sidebar: Inputs ---
with st.sidebar:
    st.header("⚙️ Configuration")
    company_name = st.text_input("Company Name", "Reliance Industries")
    uploaded_files = st.file_uploader(
        "Upload Annual Reports (PDF)", 
        type="pdf", 
        accept_multiple_files=True
    )
    
    start_btn = st.button("🚀 Run Analysis", type="primary")

# --- Main Area ---
st.title("📈 AI Financial Analyst Agent")
st.markdown("Your autonomous team for stock research, document analysis, and investment advice.")

if start_btn and company_name:
    orchestrator = OrchestratorAgent()
    
    # 1. Handle File Uploads
    pdf_paths = []
    if uploaded_files:
        with st.status("📂 Processing uploaded documents...", expanded=True):
            for file in uploaded_files:
                path = save_uploaded_file(file)
                pdf_paths.append(path)
                st.write(f"✅ Saved {file.name}")

    # 2. Run Analysis Pipeline
    with st.status("🤖 AI Agents at work...", expanded=True) as status:
        st.write("🔍 Research Agent: Fetching market data & news...")
        results = orchestrator.run_analysis(company_name, pdf_paths)
        status.update(label="✅ Analysis Complete!", state="complete", expanded=False)

    # 3. Display Results
    rec = results["recommendation"]
    data = results["market_data"]
    report = results["analysis_report"]

    # --- Top Banner: Verdict ---
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    
    color_map = {"BUY": "green", "SELL": "red", "HOLD": "orange"}
    color = color_map.get(rec.verdict, "blue")
    
    with col1:
        st.markdown(f"## Verdict: :{color}[{rec.verdict}]")
    with col2:
        st.metric("Target Entry Price", f"₹{rec.suggested_entry_price}")
    with col3:
        st.metric("Risk Score", f"{rec.risk_score}/10")

    # --- Tabs for Details ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Financial Health", "📰 Market Research", "💡 Deep Dive", "💬 Chat with Data"])

    with tab1:
        st.subheader("Financial Health Scorecard")
        score = report.score_card
        
        # Display Progress Bars for Scores
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Revenue Growth**")
            st.progress(score.revenue_growth / 10)
            st.write("**Profit Margins**")
            st.progress(score.profit_margin / 10)
            st.write("**Cash Flow**")
            st.progress(score.cash_flow / 10)
        with c2:
            st.write("**Debt Health**")
            st.progress(score.debt_health / 10)
            st.write("**ROE / ROCE**")
            st.progress(score.return_ratios / 10)
            st.write("**Earnings Consistency**")
            st.progress(score.earnings_consistency / 10)
        
        st.info(f"**Analyst Note:** {report.revenue_trend} | {report.debt_analysis}")

    with tab2:
        st.subheader("Live Market Data")
        m = data.fundamentals
        
        # Metrics Row
        rm1, rm2, rm3, rm4 = st.columns(4)
        rm1.metric("P/E Ratio", m.pe_ratio)
        rm2.metric("Market Cap", f"₹{m.market_cap} Cr")
        rm3.metric("ROE", f"{m.roe}%")
        rm4.metric("Debt/Equity", m.debt_to_equity)
        
        st.subheader("News Sentiment")
        st.warning(data.news_sentiment_summary)
        
        st.subheader("Recent Headlines")
        for news in data.news:
            st.markdown(f"- [{news.title}]({news.url})")

    with tab3:
        st.subheader("Investment Thesis")
        st.success(f"**Bull Case:** {rec.bull_case}")
        st.error(f"**Bear Case:** {rec.bear_case}")
        
        st.markdown("### 📝 Detailed Reasoning")
        st.write(rec.reasoning)

    with tab4:
        st.subheader("Ask the Document Agent")
        st.markdown("Ask specific questions about the uploaded annual reports.")
        
        user_query = st.text_input("Ask a question about the reports:")
        if user_query:
            with st.spinner("Searching documents..."):
                answer = orchestrator.document_agent.ask(company_name, user_query)
                st.markdown(f"**Answer:** {answer}")