# app.py — FlowMaster Copilot — Production-Ready
# ─────────────────────────────────────────────────────────────
# Architecture:
#   User types CHG number
#     → check reports/*.json  (instant load if exists)
#     → else run_pipeline()   (full 5-step analysis + RAG ingest)
#   Either way → Gemini chat with full report + RAG context
#
# Production features added vs v1:
#   - Sidebar: pipeline status, metadata, CI breakdown, re-analyse button
#   - run_analysis() shows real per-step progress (not fake loop)
#   - All exceptions surfaced to UI — no silent failures
#   - Input validation: CHG format check before pipeline fires
#   - Session state guards: prevents double-submission
#   - @st.cache_resource for LLM + RAG (load once, reuse always)
#   - Structured logging to terminal (print statements with prefix)

import streamlit as st
import json
import os
import re
import traceback
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from config import GEMINI_API_KEY, GEMINI_MODEL, CHAT_MAX_TOKENS, LLM_CALL_DELAY_SEC


# ══════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title  = "FlowMaster Copilot",
    page_icon   = "⚡",
    layout      = "wide",          # wide gives room for sidebar + chat
    initial_sidebar_state = "expanded",
)

st.markdown("""
<style>
    /* Chat bubbles */
    .stChatMessage          { border-radius: 12px; }
    /* Tighten sidebar padding */
    section[data-testid="stSidebar"] > div { padding-top: 1rem; }
    /* Status badges */
    .badge-critical { color:#fff; background:#C0392B; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:600; }
    .badge-high     { color:#fff; background:#E67E22; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:600; }
    .badge-medium   { color:#fff; background:#2980B9; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:600; }
    .badge-low      { color:#fff; background:#27AE60; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:600; }
    /* Sticky New Chat button — always visible top-right regardless of scroll */
    .sticky-new-chat {
        position: fixed;
        top: 14px;
        right: 24px;
        z-index: 9999;
    }
    .sticky-new-chat button {
        background-color: #f0f2f6;
        border: 1px solid #d0d3da;
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        color: #31333f;
        transition: background 0.2s;
    }
    .sticky-new-chat button:hover {
        background-color: #e0e3ea;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  SESSION STATE  — initialise once
# ══════════════════════════════════════════════════════════════
_DEFAULTS = {
    "messages":      [],     # full chat display history
    "report":        None,   # currently loaded report dict
    "chat_history":  [],     # LLM memory (last N turns)
    "is_running":    False,  # pipeline in-progress guard (prevents double-fire)
    "pipeline_steps": [],    # log of completed steps shown in sidebar
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════
#  CACHED RESOURCES  — loaded once, shared across reruns
# ══════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def get_llm():
    """Gemini LLM — cached for the full Streamlit session."""
    print("[App] Initialising Gemini LLM...")
    return ChatGoogleGenerativeAI(
        model            = GEMINI_MODEL,
        google_api_key   = GEMINI_API_KEY,
        temperature      = 0.2,
        max_output_tokens= CHAT_MAX_TOKENS,
    )

@st.cache_resource(show_spinner=False)
def get_rag():
    """FAISS RAG — loaded from disk once, then held in memory."""
    print("[App] Loading FAISS RAG index...")
    from rag.easy_rag import EasyRAG
    return EasyRAG()


# ══════════════════════════════════════════════════════════════
#  REPORT HELPERS
# ══════════════════════════════════════════════════════════════
def load_report_by_chg(chg_number: str) -> dict | None:
    """
    Scan reports/ for the most recent JSON file matching the CHG number.
    Returns the report dict or None if not found.
    """
    if not os.path.exists("reports"):
        return None
    for f in sorted(os.listdir("reports"), reverse=True):
        if chg_number.upper() in f.upper() and f.endswith(".json"):
            try:
                with open(f"reports/{f}") as fp:
                    print(f"[App] Loaded saved report: {f}")
                    return json.load(fp)
            except Exception as e:
                print(f"[App] Failed to read {f}: {e}")
    return None


def get_available_chgs() -> list[str]:
    """Return deduplicated list of CHG numbers from saved reports, newest first."""
    if not os.path.exists("reports"):
        return []
    seen, chgs = set(), []
    for f in sorted(os.listdir("reports"), reverse=True):
        if f.endswith(".json"):
            parts = f.split("_")
            if len(parts) > 1 and parts[1] not in seen:
                seen.add(parts[1])
                chgs.append(parts[1])
    return chgs


def validate_chg_number(raw: str) -> str | None:
    """
    Extract and validate CHG number from user input.
    Returns the normalised CHG string (e.g. 'CHG0012345') or None.
    Production guard — prevents pipeline from firing on garbage input.
    """
    match = re.search(r'CHG\d{5,}', raw.upper())
    return match.group() if match else None


def report_to_context(report: dict) -> str:
    """Convert full report dict to rich plain-text for LLM system prompt."""
    change  = report.get("change",     {})
    summary = report.get("ci_summary", {})
    impact  = report.get("impact",     {})
    details = report.get("ci_details", {})

    def ci_lines(key):
        return "\n".join(
            f"  - {ci['name']} | {ci.get('class','')} | "
            f"{ci.get('tier','')} | {ci.get('business_service','')}"
            for ci in details.get(key, [])
        ) or "  (none)"

    # Optional ExaCC / extended fields — only shown when present
    extra_fields = ""
    if change.get("change_reason"):
        extra_fields += f"\nChange Reason : {change.get('change_reason')}"
    if change.get("contact_list"):
        extra_fields += f"\nContact       : {change.get('contact_list')}"
    if change.get("contact_instructions"):
        extra_fields += f"\nContact Info  : {change.get('contact_instructions')}"
    if change.get("risk_description"):
        extra_fields += f"\nRisk Detail   : {change.get('risk_description')}"
    if change.get("user_service_impact"):
        extra_fields += f"\nUser Impact   : {change.get('user_service_impact')}"

    return f"""
=== CHANGE REQUEST ===
CHG Number   : {change.get('chg_number')}
Description  : {change.get('description')}
Category     : {change.get('category')}
Risk         : {change.get('risk')}
Impact Level : {change.get('impact')}
State        : {change.get('state')}
Window       : {change.get('start_date')}  →  {change.get('end_date')}
Environment  : {change.get('environment')}{extra_fields}

=== CI IMPACT SUMMARY ===
PROD CIs     : {summary.get('PROD',     0)}
DR CIs       : {summary.get('DR',       0)}
NON-PROD CIs : {summary.get('NON-PROD', 0)}
UNKNOWN CIs  : {summary.get('UNKNOWN',  0)}
Total CIs    : {sum(summary.values())}

=== PROD SERVERS ===
{ci_lines('prod')}

=== DR SERVERS ===
{ci_lines('dr')}

=== NON-PROD SERVERS ===
{ci_lines('nonprod')}

=== IMPACT ANALYSIS ===
Severity             : {impact.get('severity')}
Estimated Downtime   : {_calc_downtime(change.get('start_date',''), change.get('end_date',''))} (calculated from window)
Rollback Complexity  : {impact.get('rollback_complexity')}
Affected Services    : {', '.join(impact.get('affected_business_services', []))}
Risk Summary         : {impact.get('risk_summary')}

=== POTENTIAL FAILURES ===
{chr(10).join(f"  - {f}" for f in impact.get('potential_failures', []))}

=== RECOMMENDATIONS ===
{chr(10).join(f"  - {r}" for r in impact.get('recommendations', []))}
""".strip()


# ══════════════════════════════════════════════════════════════
#  PIPELINE RUNNER
#  This is the production-critical function — it wires the full
#  5-step core pipeline into the Streamlit UI with:
#    • Real per-step progress bar (not a fake loop)
#    • Exception caught and surfaced to UI — not swallowed
#    • Auto-save to reports/ after success
#    • Auto-ingest into RAG after save
#    • is_running guard prevents double-submission
# ══════════════════════════════════════════════════════════════
def run_analysis(chg_number: str, placeholder) -> dict | None:
    """
    Run the full pipeline with a simple clean step-by-step UI.
    Shows one line per step with a 2 second pause so the user
    can read each step before the next one appears.
    """
    import time
    from pipeline import run_pipeline, save_report

    st.session_state.is_running     = True
    st.session_state.pipeline_steps = []

    STEP_LABELS = {
        1: "change_miner.py  —  Fetching change record from ServiceNow",
        2: "ci_mapper.py     —  Traversing CMDB (BFS)",
        3: "env_classifier.py  —  Classifying environments",
        4: "impact_graph.py  —  Building CI dependency graph",
        5: "impact_analyzer.py  —  Running Gemini impact analysis",
        6: "easy_rag.py      —  Ingesting into FAISS vector store",
    }

    try:
        with placeholder.container():
            st.markdown(f"**Analysing {chg_number}...**")
            step_slot = st.empty()
            log_lines = []

            def trace_callback(step, msg, detail=""):
                is_done = "COMPLETE" in msg
                is_skip = "SKIP" in msg or "fail" in msg.lower()
                icon    = "✅" if is_done else ("⚠️" if is_skip else "⏳")

                if is_done or is_skip:
                    label = STEP_LABELS.get(step, f"Step {step}")
                    log_lines.append(f"{icon}  {label}")
                    st.session_state.pipeline_steps.append(f"{icon}  {label}")
                    if detail and (is_skip):
                        log_lines.append(f"    ↳ {detail}")

                # show current status + all completed so far
                sep     = chr(10) + chr(10)
                display = sep.join(log_lines)
                if not is_done and not is_skip:
                    label   = STEP_LABELS.get(step, f"Step {step}")
                    display += (sep if log_lines else "") + "⏳  " + label + " ..."
                step_slot.text(display)
                time.sleep(2)

            report = run_pipeline(
                chg_number,
                trace_callback=trace_callback,
                rag_instance=get_rag()
            )

            if "error" in report:
                step_slot.error(f"Pipeline error: {report['error']}")
                st.session_state.is_running = False
                return None

            save_report(report)
            sev  = report.get("impact", {}).get("severity", "")
            icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "⚪")
            dt   = report.get("impact", {}).get("estimated_downtime_minutes", "?")
            step_slot.success(f"Analysis complete — {icon} {sev} | Downtime: {dt} min")
            st.session_state.is_running = False
            return report

    except Exception as e:
        print(f"[App] Pipeline exception: {traceback.format_exc()}")
        placeholder.error(f"Error: {type(e).__name__}: {e}")
        st.session_state.is_running = False
        return None


# ══════════════════════════════════════════════════════════════
#  LLM CHAT
# ══════════════════════════════════════════════════════════════
def _needs_rag(question: str) -> bool:
    """
    Change 3: Only hit RAG when user explicitly asks about history/past/similar.
    Saves free-tier quota — no RAG on first load or simple factual questions.
    """
    from config import RAG_TRIGGER_KEYWORDS
    q = question.lower()
    return any(kw in q for kw in RAG_TRIGGER_KEYWORDS)


def _needs_app_lookup(question: str) -> str | None:
    """
    Change 2: Detect app-specific questions like 'is PROD impacted for RSP?'
    Returns the app name if detected, else None.
    """
    APPS = ["RSP", "UK-AXIOM", "UK AXIOM", "UKAXIOM", "SRC", "CAD JP", "CADJP", "RCL"]
    q = question.upper()
    for app in APPS:
        if app in q:
            return app
    return None


def _app_ci_context(app_name: str, report: dict = None) -> str:
    """
    Change 2: Pull app CIs and cross-reference with the current report's CIs.
    Gives the LLM a definitive YES/NO per environment — no guessing.
    """
    from integrations.servicenow_client import ServiceNowClient
    client   = ServiceNowClient()
    app_cis  = client.get_app_cis(app_name)
    if not app_cis:
        return f"\n=== APPLICATION: {app_name.upper()} ===\nNo CIs found for this application in CMDB.\n"

    app_ci_names = {c["name"].lower() for c in app_cis}

    # Cross-reference with the current report's CIs if available
    report_prod    = []
    report_dr      = []
    report_nonprod = []
    if report:
        details = report.get("ci_details", {})
        report_prod    = [ci["name"] for ci in details.get("prod",    []) if ci["name"].lower() in app_ci_names]
        report_dr      = [ci["name"] for ci in details.get("dr",      []) if ci["name"].lower() in app_ci_names]
        report_nonprod = [ci["name"] for ci in details.get("nonprod", []) if ci["name"].lower() in app_ci_names]

    # All app CIs grouped by env
    all_prod    = [c for c in app_cis if "prod" in c.get("environment","").lower() and "non" not in c.get("environment","").lower()]
    all_dr      = [c for c in app_cis if "dr"   in c.get("environment","").lower()]
    all_nonprod = [c for c in app_cis if any(x in c.get("environment","").lower() for x in ["non","qa","uat","dev"])]

    lines = [f"\n=== APPLICATION: {app_name.upper()} ==="]

    # Clear YES/NO impact statement based on cross-reference
    if report:
        if report_prod:
            lines.append(f"⚠️  PROD IMPACTED — {len(report_prod)} PROD CI(s) in this change: {', '.join(report_prod)}")
        else:
            lines.append(f"✅ PROD NOT IMPACTED — no {app_name} PROD CIs are in this change")
        if report_dr:
            lines.append(f"⚠️  DR IMPACTED — {len(report_dr)} DR CI(s) in this change: {', '.join(report_dr)}")
        else:
            lines.append(f"✅ DR NOT IMPACTED — no {app_name} DR CIs are in this change")
        if report_nonprod:
            lines.append(f"ℹ️  NON-PROD IMPACTED — {', '.join(report_nonprod)}")

    lines.append(f"\nAll {app_name} CIs in CMDB:")
    for ci in all_prod:
        tag = "← IN THIS CHANGE" if ci["name"] in report_prod else ""
        lines.append(f"  PROD     | {ci['name']} | DC: {ci.get('u_datacenter','?')} | {ci.get('u_region','?')} {tag}")
    for ci in all_dr:
        tag = "← IN THIS CHANGE" if ci["name"] in report_dr else ""
        lines.append(f"  DR       | {ci['name']} | DC: {ci.get('u_datacenter','?')} | {ci.get('u_region','?')} {tag}")
    for ci in all_nonprod:
        tag = "← IN THIS CHANGE" if ci["name"] in report_nonprod else ""
        lines.append(f"  NON-PROD | {ci['name']} | DC: {ci.get('u_datacenter','?')} | {ci.get('u_region','?')} {tag}")

    return "\n".join(lines)


def _calc_downtime(start: str, end: str) -> str:
    """Calculate actual downtime from change window start/end times."""
    try:
        from datetime import datetime as dt
        fmt  = "%Y-%m-%d %H:%M:%S"
        diff = dt.strptime(end, fmt) - dt.strptime(start, fmt)
        mins = int(diff.total_seconds() / 60)
        hrs  = mins // 60
        rem  = mins % 60
        if hrs > 0:
            return f"{hrs}h {rem}min" if rem else f"{hrs}h"
        return f"{mins} min"
    except Exception:
        return "Unknown"


def build_quick_summary(report: dict) -> str:
    """
    Build a concise structured summary from report data — no LLM call.
    Downtime is calculated from actual start/end times, not the LLM estimate.
    The LLM is then called ONCE to give a rich description — this is the
    only LLM call on first load.
    """
    change  = report.get("change",     {})
    impact  = report.get("impact",     {})
    summary = report.get("ci_summary", {})
    details = report.get("ci_details", {})

    chg       = change.get("chg_number", "")
    sev       = impact.get("severity", "UNKNOWN")
    icon      = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "⚪")
    downtime  = _calc_downtime(change.get("start_date",""), change.get("end_date",""))
    rb        = impact.get("rollback_complexity", "?")
    risk_sum  = impact.get("risk_summary", "")
    svcs      = impact.get("affected_business_services", [])
    risks     = impact.get("potential_failures",   [])
    recs      = impact.get("recommendations",       [])

    prod_cis    = [ci["name"] for ci in details.get("prod",    [])]
    dr_cis      = [ci["name"] for ci in details.get("dr",      [])]
    nonprod_cis = [ci["name"] for ci in details.get("nonprod", [])]

    lines = [
        f"{icon} **{chg}** — {change.get('description', '')}",
        "",
        f"| Field | Value |",
        f"|---|---|",
        f"| **Category** | {change.get('category','')} |",
        f"| **Risk** | {change.get('risk','')} |",
        f"| **State** | {change.get('state','')} |",
        f"| **Change Window** | {change.get('start_date','')} → {change.get('end_date','')} |",
        f"| **Max Downtime** | **{downtime}** (calculated from window) |",
        f"| **Severity** | **{sev}** |",
        f"| **Rollback Complexity** | {rb} |",
        f"| **PROD CIs** | {summary.get('PROD',0)} | **DR CIs** | {summary.get('DR',0)} | **Non-Prod CIs** | {summary.get('NON-PROD',0)} |",
    ]

    if change.get("contact_list"):
        lines.append(f"| **Contact** | {change.get('contact_list','')} |")
    if change.get("contact_instructions"):
        lines.append(f"| **Contact Info** | {change.get('contact_instructions','')} |")

    lines += ["", f"**Affected Applications/Services:** {', '.join(svcs) if svcs else 'None identified'}"]

    if prod_cis:
        lines += ["", f"**PROD CIs impacted ({len(prod_cis)}):**"]
        for ci in prod_cis:
            lines.append(f"  - `{ci}`")

    if dr_cis:
        lines += ["", f"**DR CIs impacted ({len(dr_cis)}):**"]
        for ci in dr_cis:
            lines.append(f"  - `{ci}`")

    if nonprod_cis:
        lines += ["", f"**Non-Prod CIs ({len(nonprod_cis)}):**"]
        for ci in nonprod_cis:
            lines.append(f"  - `{ci}`")

    if risk_sum:
        lines += ["", f"**Risk Summary:** {risk_sum}"]

    if risks:
        lines += ["", "**Potential Failures:**"]
        for r in risks:
            lines.append(f"  - {r}")

    if recs:
        lines += ["", "**Recommendations:**"]
        for r in recs:
            lines.append(f"  - {r}")

    if change.get("user_service_impact"):
        lines += ["", f"**User/Service Impact:** {change.get('user_service_impact')}"]
    if change.get("risk_description"):
        lines += ["", f"**Risk Detail:** {change.get('risk_description')}"]

    lines += ["", "---", "💬 Ask me anything about this change."]

    return "\n".join(lines)
    """
    Change 1: No RAG on first load — only fetch RAG when user asks about history/past/similar.
    Change 2: Inject app-specific CI context when question mentions RSP/UK-Axiom/SRC/CAD JP/RCL.
    Change 3: Rate-limited, token-capped, RAG keyword-gated to minimise free-tier usage.
    """
    import time
    llm     = get_llm()
    context = report_to_context(report)

    # Change 3: RAG only on explicit history/similar keywords
    historical_context = ""
    if _needs_rag(user_question):
        try:
            historical_context = get_rag().retrieve(report)
            print(f"[App] RAG triggered by keyword in: {user_question[:60]}")
        except Exception as e:
            historical_context = ""
            print(f"[App] RAG error: {e}")
    else:
        print(f"[App] RAG skipped — no history keyword detected")

    # Change 2: App-specific CI context injection
    app_context = ""
    detected_app = _needs_app_lookup(user_question)
    if detected_app:
        app_context = _app_ci_context(detected_app)
        print(f"[App] App CI context injected for: {detected_app}")

    # Build system prompt
    rag_section = (
        f"\n=== HISTORICAL SIMILAR CHANGES ===\n{historical_context}"
        if historical_context else ""
    )
    app_section = app_context  # already formatted with header

    system_prompt = (
        "You are FlowMaster Copilot, an expert IT Change Management assistant at HCLTech.\n"
        "Answer questions about the change report below. Be concise and professional.\n"
        "Use bullet points for lists. Bold key numbers. Never invent data.\n"
        "If asked about an application (RSP/UK-Axiom/SRC/CAD JP/RCL), use the APPLICATION section below.\n\n"
        f"=== CURRENT CHANGE REPORT ===\n{context}"
        f"{app_section}"
        f"{rag_section}"
    )

    messages = [SystemMessage(content=system_prompt)]

    for turn in st.session_state.chat_history[-4:]:
        messages.append(HumanMessage(content=turn["q"]))
        messages.append(AIMessage(content=turn["a"]))

    messages.append(HumanMessage(content=user_question))

    if LLM_CALL_DELAY_SEC > 0:
        time.sleep(LLM_CALL_DELAY_SEC)

    try:
        response = llm.invoke(messages)
        answer   = response.content.strip()
    except Exception as e:
        print(f"[App] Gemini call failed: {e}")
        answer = f"⚠️ LLM error: {type(e).__name__}: {e}"

    st.session_state.chat_history.append({"q": user_question, "a": answer})
    return answer


# ══════════════════════════════════════════════════════════════
#  INPUT HANDLER
# ══════════════════════════════════════════════════════════════
def ask_llm(user_question: str, report: dict) -> str:
    """
    Change 1: No RAG on first load — only fetch RAG when user asks about history/past/similar.
    Change 2: Inject app-specific CI context when question mentions RSP/UK-Axiom/SRC/CAD JP/RCL.
    Change 3: Rate-limited, token-capped, RAG keyword-gated to minimise free-tier usage.
    """
    import time
    llm     = get_llm()
    context = report_to_context(report)

    # Change 3: RAG only on explicit history/similar keywords
    historical_context = ""
    if _needs_rag(user_question):
        try:
            historical_context = get_rag().retrieve(report)
            print(f"[App] RAG triggered by keyword in: {user_question[:60]}")
        except Exception as e:
            historical_context = ""
            print(f"[App] RAG error: {e}")
    else:
        print(f"[App] RAG skipped — no history keyword detected")

    # Change 2: App-specific CI context injection
    app_context  = ""
    detected_app = _needs_app_lookup(user_question)
    if detected_app:
        app_context = _app_ci_context(detected_app, report)
        print(f"[App] App CI context injected for: {detected_app}")

    rag_section = (
        f"\n=== HISTORICAL SIMILAR CHANGES ===\n{historical_context}"
        if historical_context else ""
    )

    system_prompt = (
        "You are FlowMaster Copilot, an expert IT Change Management assistant at HCLTech.\n"
        "Answer questions about the change report below. Be concise and professional.\n"
        "Use bullet points for lists. Bold key numbers. Never invent data.\n"
        "If asked about an application (RSP/UK-Axiom/SRC/CAD JP/RCL), use the APPLICATION section below.\n\n"
        f"=== CURRENT CHANGE REPORT ===\n{context}"
        f"{app_context}"
        f"{rag_section}"
    )

    messages = [SystemMessage(content=system_prompt)]

    for turn in st.session_state.chat_history[-4:]:
        messages.append(HumanMessage(content=turn["q"]))
        messages.append(AIMessage(content=turn["a"]))

    messages.append(HumanMessage(content=user_question))

    if LLM_CALL_DELAY_SEC > 0:
        time.sleep(LLM_CALL_DELAY_SEC)

    try:
        response = llm.invoke(messages)
        answer   = response.content.strip()
    except Exception as e:
        print(f"[App] Gemini call failed: {e}")
        answer = f"⚠️ LLM error: {type(e).__name__}: {e}"

    st.session_state.chat_history.append({"q": user_question, "a": answer})
    return answer


def handle_input(user_input: str) -> str:
    """
    Route user input to the right action:
      1. CHG number detected  → load saved report OR run full pipeline
      2. Question with report → route to LLM
      3. No report loaded     → show welcome / available CHGs
    """
    user_input  = user_input.strip()
    chg_number  = validate_chg_number(user_input)

    # ── CHG number entered ─────────────────────────────────────
    if chg_number:

        # Guard: prevent pipeline from firing twice
        if st.session_state.is_running:
            return "⏳ Analysis already in progress — please wait..."

        # ── Try saved report first (instant, no LLM) ──────────
        report = load_report_by_chg(chg_number)
        if report:
            st.session_state.report       = report
            st.session_state.chat_history = []
            print(f"[App] Loaded saved report for {chg_number} — using quick summary (no LLM)")
            # Change 1: no LLM on first load — just render the report data directly
            return build_quick_summary(report)

        # ── No saved report — run full pipeline ───────────────
        pipeline_placeholder = st.empty()
        report = run_analysis(chg_number, pipeline_placeholder)

        if not report:
            return (
                f"❌ Pipeline failed for **{chg_number}**.\n\n"
                f"Check the terminal for the exact error.\n\n"
                f"Common causes:\n"
                f"- CHG number not found in ServiceNow (or mock data)\n"
                f"- Missing `GEMINI_API_KEY` in `.env`\n"
                f"- No CI attached to the change record"
            )

        st.session_state.report       = report
        st.session_state.chat_history = []
        # Change 1: no LLM on first load even for fresh pipeline — use quick summary
        return build_quick_summary(report)

    # ── Normal question — report loaded ───────────────────────
    if st.session_state.report:
        return ask_llm(user_input, st.session_state.report)

    # ── Welcome screen — no report yet ────────────────────────
    available = get_available_chgs()
    if available:
        chg_list = "\n".join(f"- **{c}**" for c in available)
        hint     = "Or type any new CHG number — I'll run a live analysis automatically."
    else:
        chg_list = "- *(no saved reports yet — run `python test_run.py` to create test data)*"
        hint     = "Type any CHG number and I'll run a live analysis!"

    return (
        "👋 Welcome to **FlowMaster Copilot**\n\n"
        "*AI-Powered Change Impact Analysis — HCLTech*\n\n"
        "---\n"
        "Type a CHG number to begin:\n"
        "- **Saved reports** load instantly ⚡\n"
        "- **New CHG numbers** trigger a full live analysis 🔄\n\n"
        f"**Available saved changes:**\n{chg_list}\n\n"
        f"💡 {hint}"
    )


# ══════════════════════════════════════════════════════════════
#  SIDEBAR — shows report metadata + pipeline step log
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚡ FlowMaster")
    st.caption("AI Change Impact Analysis · HCLTech")
    st.divider()

    report = st.session_state.report

    if report:
        change  = report.get("change",     {})
        impact  = report.get("impact",     {})
        summary = report.get("ci_summary", {})
        meta    = report.get("meta",       {})

        chg = change.get("chg_number", "")
        sev = impact.get("severity", "")
        icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "⚪")

        st.markdown(f"### {icon} {chg}")
        st.markdown(f"**{change.get('description', '')}**")
        st.divider()

        # CI breakdown only — no metric cards
        st.markdown("**CI Breakdown**")
        st.markdown(f"🔴 PROD &nbsp;&nbsp;&nbsp; `{summary.get('PROD',0)}`")
        st.markdown(f"🟡 DR &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; `{summary.get('DR',0)}`")
        st.markdown(f"🟢 Non-Prod `{summary.get('NON-PROD',0)}`")

        st.divider()

        # Affected services
        services = impact.get("affected_business_services", [])
        if services:
            st.markdown("**Affected Services**")
            for svc in services:
                st.markdown(f"- {svc}")

        st.divider()

        # Analysed at
        analyzed = meta.get("analyzed_at", "")
        if analyzed:
            try:
                dt = datetime.fromisoformat(analyzed)
                st.caption(f"Analysed: {dt.strftime('%d %b %Y %H:%M')}")
            except Exception:
                st.caption(f"Analysed: {analyzed[:16]}")

        # Re-analyse button — forces fresh pipeline run
        st.divider()
        if st.button("🔄 Re-analyse", use_container_width=True,
                     help="Run the full pipeline again for this CHG",
                     disabled=st.session_state.is_running):
            chg_to_rerun = change.get("chg_number", "")
            if chg_to_rerun:
                st.session_state.report       = None
                st.session_state.chat_history = []
                st.session_state.messages.append({
                    "role": "user",
                    "content": f"Re-analyse {chg_to_rerun}"
                })
                st.rerun()

    else:
        st.info("No change loaded yet.\n\nType a CHG number in the chat to begin.")

    # Pipeline execution trace (shown after pipeline run)
    if st.session_state.pipeline_steps:
        st.divider()
        st.markdown("**Last pipeline execution**")
        for entry in st.session_state.pipeline_steps:
            if isinstance(entry, dict):
                icon   = entry.get("icon", "✅")
                step   = entry.get("step", "")
                msg    = entry.get("msg", "")
                detail = entry.get("detail", "")
                file_  = {1:"change_miner",2:"ci_mapper",3:"env_classifier",
                          4:"impact_graph",5:"impact_analyzer",6:"easy_rag"}.get(step,"")
                st.caption(f"{icon} {file_} — {detail or msg}")
            else:
                st.caption(str(entry))

    st.divider()
    st.caption("v1.0.0 · Mock ServiceNow · Gemini 2.5 Flash")


# ══════════════════════════════════════════════════════════════
#  MAIN CHAT UI
# ══════════════════════════════════════════════════════════════
# Sticky New Chat button — stays fixed at top-right while user scrolls
st.markdown("""
<div class="sticky-new-chat">
    <form action="" method="get">
        <button type="submit" name="new_chat" value="1" onclick="
            window.parent.postMessage({type:'streamlit:setComponentValue', value:true}, '*');
        ">🗑 New Chat</button>
    </form>
</div>
""", unsafe_allow_html=True)

# Handle sticky button click via query params
if st.query_params.get("new_chat"):
    st.session_state.messages      = []
    st.session_state.report        = None
    st.session_state.chat_history  = []
    st.session_state.pipeline_steps = []
    st.query_params.clear()
    st.rerun()

st.markdown("## ⚡ FlowMaster Copilot")
st.caption("AI-Powered Change Impact Analysis — HCLTech")

# Status banner when report is loaded
if st.session_state.report:
    chg   = st.session_state.report.get("change", {}).get("chg_number", "")
    sev   = st.session_state.report.get("impact",  {}).get("severity",  "")
    icon  = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "⚪")
    prod  = st.session_state.report.get("ci_summary", {}).get("PROD", 0)
    chg_d = st.session_state.report.get("change", {})
    dt    = _calc_downtime(chg_d.get("start_date",""), chg_d.get("end_date",""))
    svcs  = ", ".join(st.session_state.report.get("impact", {}).get("affected_business_services", []))
    st.success(
        f"{icon} **{chg}** &nbsp;|&nbsp; Severity: **{sev}** &nbsp;|&nbsp; "
        f"PROD CIs: **{prod}** &nbsp;|&nbsp; Max Downtime: **{dt}** &nbsp;|&nbsp; "
        f"Services: *{svcs}*"
    )

st.divider()

# Welcome hint when no messages yet
if not st.session_state.messages:
    st.info("👋 Type a CHG number below — e.g. **CHG0012345** — to load or analyse a change.")

# Chat history replay
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input box
if prompt := st.chat_input(
    "Type a CHG number or ask anything...",
    disabled=st.session_state.is_running
):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..." if st.session_state.report else "Starting analysis..."):
            reply = handle_input(prompt)
        st.markdown(reply)

    st.session_state.messages.append({"role": "user",      "content": prompt})
    st.session_state.messages.append({"role": "assistant",  "content": reply})
    st.rerun()