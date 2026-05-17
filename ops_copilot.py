# ops_copilot.py — OpsCopilot (updated for new LangChain)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from config import GEMINI_API_KEY, GEMINI_MODEL


class OpsCopilot:
    def __init__(self, report: dict):
        self.report  = report
        self.context = self._build_context(report)
        self.history = []

        self.llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=0.2,
        )
        print("[OpsCopilot] Ready.")

    def ask(self, question: str) -> str:
        # Build messages list with history
        messages = [
            HumanMessage(content=f"""You are OpsCopilot, an IT Change Management assistant.
Use ONLY this report data to answer. Be concise and use bullet points for lists.
If answer is not in the data say 'I don't have that information.'

=== REPORT CONTEXT ===
{self.context}
"""),
        ]

        # Add last 3 turns of history
        for turn in self.history[-3:]:
            messages.append(HumanMessage(content=turn["q"]))
            messages.append(AIMessage(content=turn["a"]))

        # Add current question
        messages.append(HumanMessage(content=question))

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
        summary = report.get("ci_summary", {})
        impact  = report.get("impact",     {})
        details = report.get("ci_details", {})

        prod_names    = [ci["name"] for ci in details.get("prod",    [])]
        dr_names      = [ci["name"] for ci in details.get("dr",      [])]
        nonprod_names = [ci["name"] for ci in details.get("nonprod", [])]

        return f"""
Change     : {change.get('chg_number')} — {change.get('description')}
Category   : {change.get('category')} | Risk: {change.get('risk')}
Window     : {change.get('start_date')} to {change.get('end_date')}
Severity   : {impact.get('severity')}
Downtime   : {impact.get('estimated_downtime_minutes')} minutes
Rollback   : {impact.get('rollback_complexity')}
PROD CIs   : {', '.join(prod_names)    or 'None'}
DR CIs     : {', '.join(dr_names)      or 'None'}
NONPROD CIs: {', '.join(nonprod_names) or 'None'}
Services   : {', '.join(impact.get('affected_business_services', []))}
Risk       : {impact.get('risk_summary')}
Failures   : {'; '.join(impact.get('potential_failures', []))}
Recommend  : {'; '.join(impact.get('recommendations', []))}
""".strip()