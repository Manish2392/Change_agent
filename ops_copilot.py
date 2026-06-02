# ops_copilot.py — OpsCopilot chat assistant
# Changes for free-tier quota saving:
#   - max_output_tokens capped (CHAT_MAX_TOKENS)
#   - History trimmed from last 3 turns to last 2
#   - System context sent only once (as first message), not repeated every turn
#   - Rate limit delay before each LLM call

import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from config import GEMINI_API_KEY, GEMINI_MODEL, CHAT_MAX_TOKENS, LLM_CALL_DELAY_SEC


class OpsCopilot:
    def __init__(self, report: dict):
        self.report  = report
        self.context = self._build_context(report)
        self.history = []

        self.llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=0.2,
            max_output_tokens=CHAT_MAX_TOKENS,
        )
        print("[OpsCopilot] Ready.")

    def ask(self, question: str) -> str:
        # System context sent once as SystemMessage (cheaper than repeating in every Human turn)
        messages = [
            SystemMessage(content=(
                "You are OpsCopilot, an IT Change Management assistant. "
                "Answer ONLY from the report data below. Be concise, use bullet points for lists. "
                "If answer is not in the data say 'I don't have that information.'\n\n"
                f"=== REPORT ===\n{self.context}"
            )),
        ]

        # Only last 2 turns of history (was 3) — saves tokens on free tier
        for turn in self.history[-2:]:
            messages.append(HumanMessage(content=turn["q"]))
            messages.append(AIMessage(content=turn["a"]))

        messages.append(HumanMessage(content=question))

        # Rate limit guard
        if LLM_CALL_DELAY_SEC > 0:
            time.sleep(LLM_CALL_DELAY_SEC)

        response = self.llm.invoke(messages)
        answer   = response.content.strip()

        self.history.append({"q": question, "a": answer})
        return answer

    def interactive_session(self):
        print("\n" + "="*50)
        print("  OpsCopilot Q&A — type 'exit' to stop")
        print("="*50 + "\n")
        while True:
            try:
                question = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if question.lower() in ("exit", "quit", "q"):
                break
            if not question:
                continue
            print(f"\nCopilot: {self.ask(question)}\n")

    def _build_context(self, report: dict) -> str:
        change  = report.get("change",     {})
        impact  = report.get("impact",     {})
        details = report.get("ci_details", {})

        prod_names    = [ci["name"] for ci in details.get("prod",    [])]
        dr_names      = [ci["name"] for ci in details.get("dr",      [])]
        nonprod_names = [ci["name"] for ci in details.get("nonprod", [])]

        # Extra ExaCC fields (only shown when present — avoids padding tokens)
        extras = ""
        if change.get("contact_list"):
            extras += f"\nContact    : {change.get('contact_list')}"
        if change.get("user_service_impact"):
            extras += f"\nSvc Impact : {change.get('user_service_impact')}"
        if change.get("risk_description"):
            extras += f"\nRisk Detail: {change.get('risk_description')}"

        return (
            f"CHG: {change.get('chg_number')} — {change.get('description')}\n"
            f"Category: {change.get('category')} | Risk: {change.get('risk')}\n"
            f"Window: {change.get('start_date')} to {change.get('end_date')}\n"
            f"Severity: {impact.get('severity')} | Downtime: {impact.get('estimated_downtime_minutes')} min\n"
            f"Rollback: {impact.get('rollback_complexity')}\n"
            f"PROD: {', '.join(prod_names) or 'None'}\n"
            f"DR: {', '.join(dr_names) or 'None'}\n"
            f"NON-PROD: {', '.join(nonprod_names) or 'None'}\n"
            f"Services: {', '.join(impact.get('affected_business_services', []))}\n"
            f"Risk: {impact.get('risk_summary')}\n"
            f"Failures: {'; '.join(impact.get('potential_failures', []))}\n"
            f"Recommendations: {'; '.join(impact.get('recommendations', []))}"
            f"{extras}"
        )
