# pipeline.py — FlowMaster Central Orchestrator
# Chains all 5 steps in sequence. Supports a trace_callback so app.py
# can display a live execution log in the Streamlit UI as each step runs.

import json
from datetime import datetime
from core.change_miner    import fetch_change
from core.ci_mapper       import map_impacted_cis
from core.env_classifier  import classify_environments
from core.impact_graph    import build_impact_graph
from core.impact_analyzer import analyze_impact
from rag.easy_rag         import EasyRAG


def run_pipeline(chg_number: str, trace_callback=None, rag_instance=None) -> dict:
    """
    Full CIAP (Change Impact Analysis Pipeline) for a given CHG number.

    Parameters
    ----------
    chg_number     : ServiceNow CHG number e.g. 'CHG0001001'
    trace_callback : optional callable(step: int, msg: str, detail: str)
                     Called after each step so the caller (app.py) can
                     update a live UI trace panel in real time.
                     If None, only terminal print statements are produced.
    rag_instance   : optional pre-loaded EasyRAG instance.
                     If provided, the pipeline uses it directly — no new
                     EasyRAG() is created, so FAISS is not loaded from disk
                     twice in the same request.
                     If None, pipeline creates its own EasyRAG() as fallback.

    Steps:
      1. change_miner.py    → fetch_change()           — ServiceNow fetch
      2. ci_mapper.py       → map_impacted_cis()       — BFS CMDB traversal
      3. env_classifier.py  → classify_environments()  — PROD/DR/NonProd labeling
      4. impact_graph.py    → build_impact_graph()     — CI dependency graph
      5. impact_analyzer.py → analyze_impact()         — Gemini LLM analysis
      6. RAG ingest                                     — FAISS vector store update

    Returns the complete structured report dict, or {"error": "..."} on failure.
    """

    def trace(step, msg, detail=""):
        """Fire terminal log + optional UI callback after each step."""
        line = f"[Pipeline] Step {step}: {msg}"
        if detail:
            line += f" | {detail}"
        print(line)
        if trace_callback:
            trace_callback(step, msg, detail)

    started_at = datetime.now()
    print(f"\n{'='*60}")
    print(f"  FlowMaster CIAP starting for: {chg_number}")
    print(f"{'='*60}\n")

    try:
        # ── Step 1: change_miner.py ───────────────────────────────
        trace(1, "change_miner.py → fetch_change()", f"Fetching {chg_number} from ServiceNow...")
        change_data = fetch_change(chg_number)
        primary_ci  = change_data.get("primary_ci_id", "")
        trace(1, "change_miner.py ✓ COMPLETE",
              f"'{change_data.get('description','')[:55]}' | CI: {primary_ci}")

        if not primary_ci:
            return {"error": f"No primary CI linked to {chg_number}. "
                             f"Ensure a CI is attached in ServiceNow."}

        # ── Step 2: ci_mapper.py ──────────────────────────────────
        trace(2, "ci_mapper.py → map_impacted_cis()", f"BFS traversal from: {primary_ci}")
        all_cis = map_impacted_cis(primary_ci)
        trace(2, "ci_mapper.py ✓ COMPLETE", f"{len(all_cis)} CIs discovered via BFS")

        # ── Step 3: env_classifier.py ────────────────────────────
        trace(3, "env_classifier.py → classify_environments()", f"Classifying {len(all_cis)} CIs...")
        classified = classify_environments(all_cis)
        s = classified["summary"]
        trace(3, "env_classifier.py ✓ COMPLETE",
              f"PROD={s['PROD']}  DR={s['DR']}  NonProd={s['NON-PROD']}  Unknown={s['UNKNOWN']}")

        # ── Step 4: impact_graph.py ──────────────────────────────
        trace(4, "impact_graph.py → build_impact_graph()", f"Building graph for {len(all_cis)} CIs...")
        graph = build_impact_graph(all_cis)
        trace(4, "impact_graph.py ✓ COMPLETE",
              f"{len(graph.get('nodes',[]))} nodes  {len(graph.get('edges',[]))} edges")

        # ── Step 5: impact_analyzer.py ──────────────────────────
        trace(5, "impact_analyzer.py → analyze_impact()", "Calling Gemini 2.5 Flash for impact analysis...")
        impact = analyze_impact(change_data, classified, graph)
        trace(5, "impact_analyzer.py ✓ COMPLETE",
              f"Severity={impact.get('severity')}  Downtime={impact.get('estimated_downtime_minutes')}min  "
              f"Rollback={impact.get('rollback_complexity')}")

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

        # ── Step 6: RAG ingest ───────────────────────────────────
        # Use the passed-in rag_instance if available (avoids loading
        # FAISS from disk twice when app.py already has it cached).
        # Falls back to creating a new EasyRAG() if called standalone.
        trace(6, "easy_rag.py → rag.ingest()", "Ingesting report into FAISS vector store...")
        try:
            rag = rag_instance if rag_instance is not None else EasyRAG()
            rag.ingest(report)
            trace(6, "easy_rag.py ✓ COMPLETE", "Report indexed in FAISS for future similarity search")
        except Exception as e:
            print(f"[Pipeline] ⚠ RAG ingest failed (non-fatal): {e}")
            if trace_callback:
                trace_callback(6, "easy_rag.py ⚠ SKIPPED", f"RAG ingest failed: {e}")

        print(f"\n{'='*60}")
        print(f"  ✓ Pipeline complete in {elapsed}s")
        print(f"  Severity : {impact.get('severity')}")
        print(f"  Downtime : {impact.get('estimated_downtime_minutes')} min")
        print(f"  PROD CIs : {s['PROD']}")
        print(f"{'='*60}\n")

        return report

    except Exception as e:
        import traceback
        print(f"[Pipeline] ✗ FAILED: {traceback.format_exc()}")
        if trace_callback:
            trace_callback(0, f"Pipeline failed: {type(e).__name__}", str(e))
        return {"error": str(e)}


def save_report(report: dict, directory: str = "./reports") -> str:
    """Save the pipeline report to a timestamped JSON file."""
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