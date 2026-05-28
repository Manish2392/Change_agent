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
from config import GEMINI_API_KEY, GEMINI_MODEL


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
        model        = GEMINI_MODEL,
        google_api_key = GEMINI_API_KEY,
        temperature  = 0.2,
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
Estimated Downtime   : {impact.get('estimated_downtime_minutes')} minutes
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
def ask_llm(user_question: str, report: dict) -> str:
    """
    Send question + full report context + RAG history to Gemini.
    Keeps last 6 turns of conversation memory.
    """
    llm     = get_llm()
    context = report_to_context(report)

    # RAG retrieval — non-fatal if it fails
    try:
        historical_context = get_rag().retrieve(report)
    except Exception as e:
        historical_context = "(No historical data available)"
        print(f"[App] RAG retrieve error test: {type(e).__name__}: {e}")

    system_prompt = f"""You are FlowMaster Copilot, an expert IT Change Management assistant at HCLTech.
You help engineers understand the impact of ServiceNow change requests.

You have access to TWO sources of information:
  1. CURRENT CHANGE REPORT — the full impact analysis for the change being discussed
  2. HISTORICAL SIMILAR CHANGES — past similar changes retrieved from the RAG vector store

Rules:
  - Use BOTH sources in your answers
  - For questions about past changes, patterns, or "what happened before" — use RAG HISTORY
  - Be professional but conversational
  - Use bullet points for lists, bold for key numbers
  - Never make up data not present in the report

=== CURRENT CHANGE REPORT ===
{context}

=== HISTORICAL SIMILAR CHANGES (RAG MEMORY) ===
{historical_context}
"""

    messages = [SystemMessage(content=system_prompt)]

    # Inject last 6 conversation turns as memory
    for turn in st.session_state.chat_history[-6:]:
        messages.append(HumanMessage(content=turn["q"]))
        messages.append(AIMessage(content=turn["a"]))

    messages.append(HumanMessage(content=user_question))

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

        # ── Try saved report first (instant) ──────────────────
        report = load_report_by_chg(chg_number)
        if report:
            st.session_state.report       = report
            st.session_state.chat_history = []
            print(f"[App] Loaded saved report for {chg_number}")
            return ask_llm(
                f"Report loaded for {chg_number} from saved data. "
                f"Give a clear summary: severity, downtime, PROD CIs affected, "
                f"top 3 risks, and key recommendations.",
                report
            )

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
        return ask_llm(
            f"Fresh analysis complete for {chg_number}. "
            f"Give a clear summary: severity, downtime, PROD CIs affected, "
            f"top 3 risks, and key recommendations.",
            report
        )

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

        # Key metrics
        col1, col2 = st.columns(2)
        col1.metric("Severity",    sev)
        col2.metric("Downtime",    f"{impact.get('estimated_downtime_minutes','?')} min")
        col1.metric("Rollback",    impact.get("rollback_complexity", "?"))
        col2.metric("Category",    change.get("category", "?"))

        st.divider()

        # CI breakdown
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
    chg  = st.session_state.report.get("change", {}).get("chg_number", "")
    sev  = st.session_state.report.get("impact",  {}).get("severity",  "")
    icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "⚪")
    prod = st.session_state.report.get("ci_summary", {}).get("PROD", 0)
    dt   = st.session_state.report.get("impact", {}).get("estimated_downtime_minutes", "-")
    svcs = ", ".join(st.session_state.report.get("impact", {}).get("affected_business_services", []))
    st.success(
        f"{icon} **{chg}** &nbsp;|&nbsp; Severity: **{sev}** &nbsp;|&nbsp; "
        f"PROD CIs: **{prod}** &nbsp;|&nbsp; Downtime: **{dt} min** &nbsp;|&nbsp; "
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

# Quick question buttons (only when report loaded)
if st.session_state.report and not st.session_state.is_running:
    st.markdown("**Quick questions:**")
    quick = [
        "Is production impacted?",
        "How long will it be down?",
        "What could go wrong?",
        "What should we do?",
        "Find similar past changes",
        "Is this safe to proceed?",
    ]
    cols = st.columns(3)
    for i, q in enumerate(quick):
        if cols[i % 3].button(q, key=f"q_{i}", use_container_width=True):
            with st.chat_message("user"):
                st.markdown(q)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    reply = handle_input(q)
                st.markdown(reply)
            st.session_state.messages.append({"role": "user",      "content": q})
            st.session_state.messages.append({"role": "assistant",  "content": reply})
            st.rerun()

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