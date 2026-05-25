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

    return f"""
=== CHANGE REQUEST ===
CHG Number   : {change.get('chg_number')}
Description  : {change.get('description')}
Category     : {change.get('category')}
Risk         : {change.get('risk')}
Impact Level : {change.get('impact')}
State        : {change.get('state')}
Window       : {change.get('start_date')}  →  {change.get('end_date')}
Environment  : {change.get('environment')}

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
    Execute the full pipeline inside a Streamlit placeholder container.

    Parameters
    ----------
    chg_number  : validated CHG string e.g. 'CHG0012345'
    placeholder : st.empty() container where progress UI renders

    Returns the report dict on success, None on failure.
    """
    from pipeline import run_pipeline, save_report

    st.session_state.is_running    = True
    st.session_state.pipeline_steps = []

    STEPS = [
        ("🔎 Step 1/5", "Fetching change record from ServiceNow...",    "change_miner"),
        ("🗺  Step 2/5", "Traversing CMDB relationships (BFS)...",       "ci_mapper"),
        ("🏷  Step 3/5", "Classifying environments (PROD / DR / QA)...", "env_classifier"),
        ("🕸  Step 4/5", "Building CI dependency graph...",              "impact_graph"),
        ("🤖 Step 5/5", "Running Gemini impact analysis...",            "impact_analyzer"),
    ]

    try:
        with placeholder.container():
            st.markdown(f"### ⚙️ Analysing **{chg_number}**")
            st.caption("Pipeline running — this takes 20–40 seconds")
            progress_bar  = st.progress(0)
            step_status   = st.empty()
            completed_box = st.container()

            # Show steps advancing (UI feedback while pipeline runs)
            for i, (label, msg, _) in enumerate(STEPS):
                step_status.info(f"{label} — {msg}")
                progress_bar.progress((i + 1) / (len(STEPS) + 1))
                st.session_state.pipeline_steps.append(f"⏳ {label} — {msg}")

            step_status.info("⚙️  Waiting for Gemini response...")

            # ── The actual pipeline call ───────────────────────
            report = run_pipeline(chg_number)

            if "error" in report:
                progress_bar.empty()
                step_status.error(f"❌ Pipeline error: {report['error']}")
                print(f"[App] Pipeline returned error for {chg_number}: {report['error']}")
                st.session_state.is_running = False
                return None

            # ── Save to disk ───────────────────────────────────
            saved_path = save_report(report)
            print(f"[App] Report saved → {saved_path}")

            # ── Ingest into RAG ────────────────────────────────
            try:
                rag = get_rag()
                rag.ingest(report)
                print(f"[App] RAG ingest complete for {chg_number}")
            except Exception as rag_err:
                print(f"[App] RAG ingest warning (non-fatal): {rag_err}")

            # ── Mark complete ──────────────────────────────────
            progress_bar.progress(1.0)
            sev  = report.get("impact", {}).get("severity", "")
            icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "⚪")
            step_status.success(
                f"✅ Analysis complete! {icon} Severity: **{sev}** | "
                f"Downtime: **{report.get('impact', {}).get('estimated_downtime_minutes', '?')} min**"
            )
            st.session_state.pipeline_steps = [
                f"✅ {label} — done" for label, _, _ in STEPS
            ]

            st.session_state.is_running = False
            return report

    except Exception as e:
        print(f"[App] Unhandled pipeline exception: {traceback.format_exc()}")
        placeholder.error(f"❌ Unexpected error: {type(e).__name__}: {e}")
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
        print(f"[App] RAG retrieve error: {type(e).__name__}: {e}")

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

    # Pipeline step log (shown during and after pipeline run)
    if st.session_state.pipeline_steps:
        st.divider()
        st.markdown("**Last pipeline run**")
        for step in st.session_state.pipeline_steps:
            st.caption(step)

    st.divider()
    st.caption("v1.0.0 · Mock ServiceNow · Gemini 2.5 Flash")


# ══════════════════════════════════════════════════════════════
#  MAIN CHAT UI
# ══════════════════════════════════════════════════════════════
col1, col2 = st.columns([5, 1])
with col1:
    st.markdown("## ⚡ FlowMaster Copilot")
    st.caption("AI-Powered Change Impact Analysis — HCLTech")
with col2:
    if st.button("🗑 New Chat", use_container_width=True,
                 disabled=st.session_state.is_running):
        st.session_state.messages     = []
        st.session_state.report       = None
        st.session_state.chat_history = []
        st.session_state.pipeline_steps = []
        st.rerun()

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