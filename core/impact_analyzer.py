# core/impact_analyzer.py — Step 5: ImpactAnalyzer
# Changes for free-tier quota saving:
#   - max_output_tokens capped (IMPACT_MAX_TOKENS from config)
#   - Prompt trimmed: removed redundant graph text, shorter JSON schema hint
#   - Rate-limit delay applied before LLM call
#   - Result cached in-memory by chg_number to avoid re-analysis on re-runs

import json
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from core.impact_graph import graph_to_text
from config import GEMINI_API_KEY, GEMINI_MODEL, IMPACT_MAX_TOKENS, LLM_CALL_DELAY_SEC

# ── Simple in-memory cache (survives for the life of the process) ──
_ANALYSIS_CACHE: dict = {}


def analyze_impact(change_data: dict, classified_cis: dict, graph: dict) -> dict:
    chg = change_data.get("chg_number", "")

    # ── Cache hit: skip the LLM call entirely ──────────────────
    if chg and chg in _ANALYSIS_CACHE:
        print(f"[ImpactAnalyzer] ✓ Cache hit for {chg} — skipping LLM call")
        return _ANALYSIS_CACHE[chg]

    prod_names    = [ci["name"] for ci in classified_cis.get("prod",    [])]
    dr_names      = [ci["name"] for ci in classified_cis.get("dr",      [])]
    nonprod_names = [ci["name"] for ci in classified_cis.get("nonprod", [])]

    # ── Compact prompt: same info, ~40% fewer tokens ───────────
    prompt = f"""IT Change analyst. Return ONLY valid JSON, no markdown fences.

CHG: {chg} | {change_data['description']}
Category: {change_data['category']} | Risk: {change_data['risk']}
Window: {change_data['start_date']} to {change_data['end_date']}
PROD({len(prod_names)}): {', '.join(prod_names) or 'None'}
DR({len(dr_names)}): {', '.join(dr_names) or 'None'}
NON-PROD({len(nonprod_names)}): {', '.join(nonprod_names) or 'None'}
Graph: {graph_to_text(graph)}

Return JSON: {{
  "severity":"LOW|MEDIUM|HIGH|CRITICAL",
  "affected_business_services":["svc1"],
  "estimated_downtime_minutes":30,
  "risk_summary":"1-2 sentences",
  "recommendations":["rec1","rec2"],
  "potential_failures":["fail1"],
  "rollback_complexity":"LOW|MEDIUM|HIGH"
}}"""

    # ── Rate limit guard ───────────────────────────────────────
    if LLM_CALL_DELAY_SEC > 0:
        print(f"[ImpactAnalyzer] Waiting {LLM_CALL_DELAY_SEC}s (rate limit guard)...")
        time.sleep(LLM_CALL_DELAY_SEC)

    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
        max_output_tokens=IMPACT_MAX_TOKENS,
    )
    chain  = llm | StrOutputParser()
    result = chain.invoke(prompt)

    try:
        clean  = result.strip().replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        parsed = {"severity": "UNKNOWN", "risk_summary": result}

    parsed["raw_llm_response"] = result
    parsed.setdefault("prod_ci_count",    len(prod_names))
    parsed.setdefault("dr_ci_count",      len(dr_names))
    parsed.setdefault("nonprod_ci_count", len(nonprod_names))

    # ── Store in cache ─────────────────────────────────────────
    if chg:
        _ANALYSIS_CACHE[chg] = parsed

    print(f"[ImpactAnalyzer] ✓ Severity: {parsed.get('severity')}")
    return parsed
