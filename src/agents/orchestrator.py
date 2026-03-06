from src.agents.research_agent import ResearchAgent
from src.agents.document_agent import DocumentAgent
from src.agents.analysis_agent import AnalysisAgent
from src.agents.advisor_agent import AdvisorAgent

class OrchestratorAgent:
    def __init__(self):
        self.researcher = ResearchAgent()
        self.document_agent = DocumentAgent()
        self.analyst = AnalysisAgent()
        self.advisor = AdvisorAgent()

    def run_analysis(self, company: str, pdf_files: list[str] = None):
        """
        Executes the full stock analysis pipeline.
        
        Args:
            company: Name of the company.
            pdf_files: List of file paths to PDF documents (optional).
            
        Returns:
            Dict containing all reports and data.
        """
        results = {"company": company}

        # 1. Research (Market Data + News)
        print(f"🚀 [Orchestrator] Starting research for {company}...")
        market_data = self.researcher.analyze(company)
        results["market_data"] = market_data

        # 2. Document Processing (RAG)
        doc_insights = "No internal financial documents provided."
        if pdf_files:
            print(f"📂 [Orchestrator] Processing {len(pdf_files)} documents...")
            for pdf_path in pdf_files:
                # Ingest into Vector DB
                self.document_agent.ingest(pdf_path, company, "annual_report")
            
            # Ask RAG for a high-level summary to feed the Analyst
            doc_insights = self.document_agent.ask(
                company, 
                "Summarize the key financial risks, revenue growth, and margins from the documents."
            )
        
        results["doc_insights"] = doc_insights

        # 3. Financial Analysis (Scorecard)
        print(f"📊 [Orchestrator] Running financial analysis...")
        analysis_report = self.analyst.analyze(market_data, doc_insights)
        results["analysis_report"] = analysis_report

        # 4. Final Advice (Buy/Sell/Hold)
        print(f"💡 [Orchestrator] Getting investment advice...")
        recommendation = self.advisor.advise(market_data, analysis_report)
        results["recommendation"] = recommendation

        return results