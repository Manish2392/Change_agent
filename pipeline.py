# pipeline.py — FlowMaster Central Orchestrator
# Chains all 5 steps in sequence using LangChain. Handles errors + RAG ingestion.

import json
from datetime import datetime
from core.change_miner    import fetch_change
from core.ci_mapper       import map_impacted_cis
from core.env_classifier  import classify_environments
from core.impact_graph    import build_impact_graph
from core.impact_analyzer import analyze_impact
from rag.easy_rag         import EasyRAG


def run_pipeline(chg_number: str) -> dict:
    """
    Full CIAP (CI Analysis Pipeline) for a given CHG number.

    Steps:
      1. ChangeMiner   → Fetch CHG record from ServiceNow
      2. CI Mapper     → BFS traverse CMDB to find all impacted CIs
      3. EnvClassifier → Label each CI as PROD / DR / NON-PROD
      4. ImpactGraph   → Build CI dependency graph
      5. ImpactAnalyzer→ Gemini LLM analysis enriched with RAG history
      6. RAG Ingest    → Store this report in FAISS for future retrievals

    Returns the complete structured report dict.
    """
    started_at = datetime.now()
    print(f"\n{'='*60}")
    print(f"  FlowMaster CIAP starting for: {chg_number}")
    print(f"{'='*60}\n")

    try:
        # ── Step 1 ────────────────────────────────────────────────
        change_data = fetch_change(chg_number)
        primary_ci  = change_data.get("primary_ci_id", "")
        if not primary_ci:
            return {"error": f"No primary CI linked on {chg_number}. "
                             f"Please ensure a CI is attached in ServiceNow."}

        # ── Step 2 ────────────────────────────────────────────────
        all_cis = map_impacted_cis(primary_ci)

        # ── Step 3 ────────────────────────────────────────────────
        classified = classify_environments(all_cis)

        # ── Step 4 ────────────────────────────────────────────────
        graph = build_impact_graph(all_cis)

        # ── Step 5 ────────────────────────────────────────────────
        impact = analyze_impact(change_data, classified, graph)

        # ── Assemble report ───────────────────────────────────────
        elapsed = (datetime.now() - started_at).seconds
        report  = {
            "meta": {
                "chg_number":  chg_number,
                "analyzed_at": started_at.isoformat(),
                "elapsed_sec": elapsed,
            },
            "change":     change_data,
            "ci_summary": classified["summary"],
            "ci_details": {
                "prod":    classified["prod"],
                "dr":      classified["dr"],
                "nonprod": classified["nonprod"],
                "unknown": classified["unknown"],
            },
            "graph":  graph,
            "impact": impact,
        }

        # ── Step 6: Ingest into RAG for future retrievals ─────────
        try:
            rag = EasyRAG()
            rag.ingest(report)
        except Exception as e:
            print(f"[Pipeline] ⚠ RAG ingest failed (non-fatal): {e}")

        print(f"\n{'='*60}")
        print(f"  ✓ Pipeline complete in {elapsed}s")
        print(f"  Severity : {impact.get('severity')}")
        print(f"  Downtime : {impact.get('estimated_downtime_minutes')} min")
        print(f"  PROD CIs : {classified['summary']['PROD']}")
        print(f"{'='*60}\n")

        return report

    except Exception as e:
        print(f"[Pipeline] ✗ Pipeline failed: {e}")
        return {"error": str(e)}


def save_report(report: dict, directory: str = "./reports") -> str:
    """Save the pipeline report to a JSON file in the reports directory."""
    import os
    os.makedirs(directory, exist_ok=True)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    chg      = report.get("meta", {}).get("chg_number", "CHG")
    filename = f"{directory}/report_{chg}_{ts}.json"
    with open(filename, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"[Pipeline] Report saved → {filename}")
    return filename


def load_report(filepath: str) -> dict:
    """Load a previously saved JSON report."""
    with open(filepath) as f:
        return json.load(f)
