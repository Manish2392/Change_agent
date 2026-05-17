# app.py — FlowMaster Copilot — Full LLM-powered natural conversation
import streamlit as st
import json
import os
import re
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from config import GEMINI_API_KEY, GEMINI_MODEL

st.set_page_config(
    page_title="FlowMaster Copilot",
    page_icon="⚡",
    layout="centered",
)

st.markdown("""
<style>
    .stChatMessage { border-radius: 12px; }
    .main { max-width: 800px; }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────
for key, val in {
    "messages":      [],
    "report":        None,
    "chat_history":  [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ── LLM setup ─────────────────────────────────────────────────
@st.cache_resource
def get_llm():
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.2,
    )


def load_report_by_chg(chg_number: str):
    """Find and load a saved report matching the CHG number."""
    if not os.path.exists("reports"):
        return None
    for f in sorted(os.listdir("reports"), reverse=True):
        if chg_number.upper() in f.upper() and f.endswith(".json"):
            with open(f"reports/{f}") as fp:
                return json.load(fp)
    return None


def get_available_chgs() -> list:
    """Return list of CHG numbers from saved reports."""
    if not os.path.exists("reports"):
        return []
    chgs = []
    for f in sorted(os.listdir("reports"), reverse=True):
        if f.endswith(".json"):
            parts = f.split("_")
            if len(parts) > 1:
                chgs.append(parts[1])
    return chgs


def report_to_context(report: dict) -> str:
    """Convert full report into a detailed text block for the LLM."""
    change  = report.get("change",     {})
    summary = report.get("ci_summary", {})
    impact  = report.get("impact",     {})
    details = report.get("ci_details", {})

    prod_names    = [ci["name"] for ci in details.get("prod",    [])]
    dr_names      = [ci["name"] for ci in details.get("dr",      [])]
    nonprod_names = [ci["name"] for ci in details.get("nonprod", [])]

    return f"""
=== CHANGE REQUEST ===
CHG Number   : {change.get('chg_number')}
Description  : {change.get('description')}
Category     : {change.get('category')}
Risk         : {change.get('risk')}
Impact       : {change.get('impact')}
State        : {change.get('state')}
Start        : {change.get('start_date')}
End          : {change.get('end_date')}
Environment  : {change.get('environment')}

=== CI IMPACT SUMMARY ===
PROD CIs     : {summary.get('PROD', 0)}
DR CIs       : {summary.get('DR', 0)}
NON-PROD CIs : {summary.get('NON-PROD', 0)}
UNKNOWN CIs  : {summary.get('UNKNOWN', 0)}
Total CIs    : {sum(summary.values())}

=== PROD SERVERS ===
{chr(10).join(f"- {ci['name']} | Class: {ci.get('class','')} | Tier: {ci.get('tier','')} | Service: {ci.get('business_service','')}" for ci in details.get('prod', []))}

=== DR SERVERS ===
{chr(10).join(f"- {ci['name']} | Class: {ci.get('class','')} | Tier: {ci.get('tier','')} | Service: {ci.get('business_service','')}" for ci in details.get('dr', []))}

=== NON-PROD SERVERS ===
{chr(10).join(f"- {ci['name']} | Class: {ci.get('class','')} | Tier: {ci.get('tier','')} | Service: {ci.get('business_service','')}" for ci in details.get('nonprod', []))}

=== IMPACT ANALYSIS ===
Severity             : {impact.get('severity')}
Estimated Downtime   : {impact.get('estimated_downtime_minutes')} minutes
Rollback Complexity  : {impact.get('rollback_complexity')}
Affected Services    : {', '.join(impact.get('affected_business_services', []))}
Risk Summary         : {impact.get('risk_summary')}

=== POTENTIAL FAILURES ===
{chr(10).join(f"- {f}" for f in impact.get('potential_failures', []))}

=== RECOMMENDATIONS ===
{chr(10).join(f"- {r}" for r in impact.get('recommendations', []))}
""".strip()


def ask_llm(user_question: str, report: dict) -> str:
    """Send question + report context + RAG history to Gemini."""
    llm     = get_llm()
    context = report_to_context(report)

    # ── Pull RAG historical context ────────────────────────────
    try:
        from rag.easy_rag import EasyRAG
        rag              = EasyRAG()
        change_data      = report.get("change", {})
        historical_context = rag.retrieve(change_data)
    except Exception:
        historical_context = "(No historical data available)"

    # ── Build messages ─────────────────────────────────────────
    messages = [
        SystemMessage(content=f"""You are FlowMaster Copilot, an expert IT Change Management assistant at HCLTech.
You help engineers understand the impact of ServiceNow change requests.

You have access to TWO sources of information:

1. CURRENT CHANGE REPORT — the report you are analyzing right now
2. HISTORICAL SIMILAR CHANGES — past similar changes retrieved from RAG memory

Use BOTH sources to answer questions. When asked about past changes, 
previous incidents, or historical patterns — use the RAG HISTORY section.
Be conversational, friendly and concise. Use bullet points for lists.

=== CURRENT CHANGE REPORT ===
{context}

=== HISTORICAL SIMILAR CHANGES (RAG MEMORY) ===
{historical_context}
""")
    ]

    # Add conversation history
    for turn in st.session_state.chat_history[-6:]:
        messages.append(HumanMessage(content=turn["q"]))
        messages.append(AIMessage(content=turn["a"]))

    messages.append(HumanMessage(content=user_question))

    response = llm.invoke(messages)
    answer   = response.content.strip()

    st.session_state.chat_history.append({
        "q": user_question,
        "a": answer
    })

    return answer

def handle_input(user_input: str) -> str:
    """Main handler — detect CHG number or pass to LLM."""
    user_input = user_input.strip()

    # ── Check if user typed a CHG number ──────────────────────
    chg_match = re.search(r'CHG\d+', user_input.upper())
    if chg_match:
        chg_number = chg_match.group()
        report     = load_report_by_chg(chg_number)

        if report:
            st.session_state.report       = report
            st.session_state.chat_history = []  # reset memory for new CHG

            # Ask LLM to give a natural opening summary
            return ask_llm(
                f"I just loaded the report for {chg_number}. "
                f"Give me a clear, friendly summary of this change and its impact. "
                f"Include severity, downtime, affected services, and top risks.",
                report
            )
        else:
            available = get_available_chgs()
            return (
                f"❌ I couldn't find a report for **{chg_number}**.\n\n"
                f"**Available CHGs:**\n" +
                "\n".join(f"- {c}" for c in available)
            )

    # ── If report loaded, answer with LLM ─────────────────────
    if st.session_state.report:
        return ask_llm(user_input, st.session_state.report)

    # ── No report loaded yet ───────────────────────────────────
    available = get_available_chgs()
    chg_list  = "\n".join(f"- **{c}**" for c in available) if available else "- No reports yet — run `python test_run.py` first"

    return (
        "👋 Hi! I'm **FlowMaster Copilot**.\n\n"
        "Just type a CHG number to get started!\n\n"
        f"**Available changes:**\n{chg_list}"
    )


# ── Header ─────────────────────────────────────────────────────
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown("## ⚡ FlowMaster Copilot")
    st.markdown("*AI-Powered Change Impact Analysis — HCLTech*")
with col2:
    if st.button("🗑 New Chat", use_container_width=True):
        st.session_state.messages      = []
        st.session_state.report        = None
        st.session_state.chat_history  = []
        st.rerun()

# Show which CHG is loaded
if st.session_state.report:
    chg  = st.session_state.report.get("change", {}).get("chg_number", "")
    sev  = st.session_state.report.get("impact",  {}).get("severity",  "")
    icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "⚪")
    st.success(f"{icon} Analyzing: **{chg}** — Severity: {sev}")

st.divider()

# ── Display chat history ───────────────────────────────────────
if not st.session_state.messages:
    st.info("👋 Type a CHG number below to start — e.g. **CHG0012345**")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Quick question buttons ─────────────────────────────────────
if st.session_state.report:
    st.markdown("**Quick questions:**")
    quick = [
        "Is production impacted?",
        "How long will it be down?",
        "What could go wrong?",
        "What should we do?",
        "Which business services are affected?",
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

# ── Chat input ─────────────────────────────────────────────────
if prompt := st.chat_input("Type a CHG number or ask anything..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = handle_input(prompt)
        st.markdown(reply)

    st.session_state.messages.append({"role": "user",      "content": prompt})
    st.session_state.messages.append({"role": "assistant",  "content": reply})
    st.rerun()