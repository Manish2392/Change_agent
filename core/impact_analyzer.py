# core/impact_analyzer.py — Step 5: ImpactAnalyzer (updated for new LangChain)
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.impact_graph import graph_to_text
from config import GEMINI_API_KEY, GEMINI_MODEL

def analyze_impact(change_data: dict, classified_cis: dict, graph: dict) -> dict:
    prod_names    = [ci["name"] for ci in classified_cis.get("prod",    [])]
    dr_names      = [ci["name"] for ci in classified_cis.get("dr",      [])]
    nonprod_names = [ci["name"] for ci in classified_cis.get("nonprod", [])]

    prompt = f"""
You are an expert IT Change Management analyst.
Analyze the following change and return ONLY a valid JSON object, no extra text.

=== CHANGE DETAILS ===
Change Number : {change_data['chg_number']}
Description   : {change_data['description']}
Category      : {change_data['category']}
Risk Level    : {change_data['risk']}
Window Start  : {change_data['start_date']}
Window End    : {change_data['end_date']}

=== IMPACTED CIs ===
PROD     ({len(prod_names)}): {', '.join(prod_names) or 'None'}
DR       ({len(dr_names)}): {', '.join(dr_names) or 'None'}
NON-PROD ({len(nonprod_names)}): {', '.join(nonprod_names) or 'None'}

=== CI DEPENDENCY GRAPH ===
{graph_to_text(graph)}

Respond ONLY with this JSON structure:
{{
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "prod_ci_count": {len(prod_names)},
  "dr_ci_count": {len(dr_names)},
  "nonprod_ci_count": {len(nonprod_names)},
  "affected_business_services": ["service1", "service2"],
  "estimated_downtime_minutes": 30,
  "risk_summary": "1-2 sentence risk summary",
  "recommendations": ["recommendation 1", "recommendation 2"],
  "potential_failures": ["failure 1", "failure 2"],
  "rollback_complexity": "LOW|MEDIUM|HIGH"
}}
"""
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
    )
    chain  = llm | StrOutputParser()
    result = chain.invoke(prompt)

    try:
        clean  = result.strip().replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        parsed = {"severity": "UNKNOWN", "risk_summary": result}

    parsed["raw_llm_response"] = result
    print(f"[ImpactAnalyzer] ✓ Severity: {parsed.get('severity')}")
    return parsed