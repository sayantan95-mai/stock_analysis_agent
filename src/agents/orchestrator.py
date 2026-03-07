"""
Orchestrator Agent — the root agent that coordinates all specialist agents.
"""
import re
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
        results = {"company": company}

        # ── Step 1: Research ──
        print(f"🚀 [Orchestrator] Starting research for {company}...")
        try:
            market_data = self.researcher.analyze(company)
            results["market_data"] = market_data
        except Exception as e:
            print(f"❌ [Orchestrator] Research Agent failed: {e}")
            raise

        # ── Step 2: Document Processing ──
        doc_insights = "No internal financial documents provided."
        ingestion_results = {"success": [], "failed": []}

        if pdf_files:
            print(f"📂 [Orchestrator] Processing {len(pdf_files)} documents...")
            for pdf_path in pdf_files:
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
                        "error": error_msg[:200]
                    })
                    continue

            if ingestion_results["success"]:
                print(f"✅ [Orchestrator] Successfully ingested: {ingestion_results['success']}")
            if ingestion_results["failed"]:
                print(f"❌ [Orchestrator] Failed to ingest: {[f['file'] for f in ingestion_results['failed']]}")

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

        # ── Step 3: Analysis ──
        print(f"📊 [Orchestrator] Running financial analysis...")
        try:
            analysis_report = self.analyst.analyze(market_data, doc_insights)
            results["analysis_report"] = analysis_report
        except Exception as e:
            print(f"❌ [Orchestrator] Analysis Agent failed: {e}")
            raise

        # ── Step 4: Advice ──
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
        """Extract period from filename. Handles FY26, 2Q_FY26, 2023-24, etc."""
        name = Path(pdf_path).stem.upper()

        patterns = [
            r"(Q[1-4][-_]?FY\d{4})",       # Q3_FY2024
            r"(Q[1-4][-_]?FY\d{2})(?!\d)",  # Q3_FY26
            r"([1-4]Q[-_]?FY\d{4})",        # 2Q_FY2026
            r"([1-4]Q[-_]?FY\d{2})(?!\d)",  # 2Q_FY26
            r"(FY[-_]?\d{4}[-_]?\d{2,4})",  # FY2025-26
            r"(FY[-_]?\d{4})",               # FY2024
            r"(FY[-_]?\d{2})(?!\d)",         # FY26
            r"(Q[1-4][-_]?\d{4})",           # Q3_2024
            r"(\d{4}[-_]\d{2,4})",           # 2023-24 or 2023-2024
            r"(\d{4})",                       # 2024
        ]
        for pattern in patterns:
            match = re.search(pattern, name)
            if match:
                return match.group(1).replace("-", "_")

        return "FY2024"

    @staticmethod
    def _detect_doc_type(pdf_path: str) -> str:
        """Detect document type from filename."""
        name = Path(pdf_path).stem.lower()

        if any(kw in name for kw in ["annual", "yearly", "ar_", "integrated"]):
            return "annual_report"
        elif any(kw in name for kw in ["quarter", "q1", "q2", "q3", "q4", "1q", "2q", "3q", "4q"]):
            return "quarterly"
        elif any(kw in name for kw in ["earning", "call", "transcript"]):
            return "earnings_call"
        elif any(kw in name for kw in ["investor", "presentation", "analyst"]):
            return "investor_presentation"
        elif any(kw in name for kw in ["media", "release", "press"]):
            return "press_release"

        return "annual_report"