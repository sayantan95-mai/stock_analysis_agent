"""
Orchestrator Agent — the root agent that coordinates all specialist agents.
"""
from pathlib import Path
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

        # ── Step 1: Research (Market Data + News) ──
        print(f"🚀 [Orchestrator] Starting research for {company}...")
        try:
            market_data = self.researcher.analyze(company)
            results["market_data"] = market_data
        except Exception as e:
            print(f"❌ [Orchestrator] Research Agent failed: {e}")
            raise

        # ── Step 2: Document Processing (RAG) ──
        doc_insights = "No internal financial documents provided."
        ingestion_results = {"success": [], "failed": []}
        
        if pdf_files:
            print(f"📂 [Orchestrator] Processing {len(pdf_files)} documents...")
            for pdf_path in pdf_files:
                # Auto-detect period from filename (e.g., "Q3_FY2024.pdf" → "Q3_FY2024")
                period = self._detect_period(pdf_path)
                doc_type = self._detect_doc_type(pdf_path)

                try:
                    self.document_agent.ingest(
                        pdf_path=pdf_path,
                        company=company,
                        doc_type=doc_type,
                        period=period,
                    )
                    ingestion_results["success"].append(Path(pdf_path).name)
                except Exception as e:
                    error_msg = str(e)
                    print(f"⚠️ [Orchestrator] Failed to ingest {pdf_path}: {error_msg}")
                    ingestion_results["failed"].append({
                        "file": Path(pdf_path).name,
                        "error": error_msg[:200]  # Truncate long errors
                    })
                    continue

            # Report ingestion status
            if ingestion_results["success"]:
                print(f"✅ [Orchestrator] Successfully ingested: {ingestion_results['success']}")
            if ingestion_results["failed"]:
                print(f"❌ [Orchestrator] Failed to ingest: {[f['file'] for f in ingestion_results['failed']]}")

            # Ask RAG for a high-level summary to feed the Analyst (only if we have docs)
            if ingestion_results["success"]:
                try:
                    doc_insights = self.document_agent.ask(
                        company,
                        "Summarize the key financial risks, revenue growth, profit margins, "
                        "debt levels, and cash flow from the documents."
                    )
                except Exception as e:
                    print(f"⚠️ [Orchestrator] Document query failed: {e}")
                    doc_insights = "Document ingestion succeeded but query failed."

        results["doc_insights"] = doc_insights
        results["ingestion_results"] = ingestion_results

        # ── Step 3: Financial Analysis (Scorecard) ──
        print(f"📊 [Orchestrator] Running financial analysis...")
        try:
            analysis_report = self.analyst.analyze(market_data, doc_insights)
            results["analysis_report"] = analysis_report
        except Exception as e:
            print(f"❌ [Orchestrator] Analysis Agent failed: {e}")
            raise

        # ── Step 4: Final Advice (Buy/Sell/Hold) ──
        print(f"💡 [Orchestrator] Getting investment advice...")
        try:
            recommendation = self.advisor.advise(market_data, analysis_report)
            results["recommendation"] = recommendation
        except Exception as e:
            print(f"❌ [Orchestrator] Advisor Agent failed: {e}")
            raise

        print(f"✅ [Orchestrator] Analysis complete for {company}!")
        return results

    @staticmethod
    def _detect_period(pdf_path: str) -> str:
        """Try to extract period from filename, fallback to 'FY2024'."""
        name = Path(pdf_path).stem.upper()

        # Match patterns like Q1_FY2024, FY2023, Q3_2024
        import re
        patterns = [
            r"(Q[1-4][-_]?FY\d{4})",     # Q3_FY2024
            r"(FY[-_]?\d{4})",             # FY2024
            r"(Q[1-4][-_]?\d{4})",         # Q3_2024
            r"(\d{4}[-_]\d{4})",           # 2023-2024
            r"(\d{4})",                     # 2024
        ]
        for pattern in patterns:
            match = re.search(pattern, name)
            if match:
                return match.group(1).replace("-", "_")

        return "FY2024"  # fallback

    @staticmethod
    def _detect_doc_type(pdf_path: str) -> str:
        """Try to detect document type from filename."""
        name = Path(pdf_path).stem.lower()

        if any(kw in name for kw in ["annual", "yearly", "ar_"]):
            return "annual_report"
        elif any(kw in name for kw in ["quarter", "q1", "q2", "q3", "q4"]):
            return "quarterly"
        elif any(kw in name for kw in ["earning", "call", "transcript"]):
            return "earnings_call"
        elif any(kw in name for kw in ["investor", "presentation"]):
            return "investor_presentation"

        return "annual_report"  # fallback