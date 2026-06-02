# core/impact_analyzer.py — Step 5: ImpactAnalyzer
#
# Fixes applied:
#   1. thinking_budget=0  — disables CoT on this structured-output task;
#      without this, gemini-2.5-flash / flash-lite burns the entire
#      max_output_tokens budget on reasoning before writing any JSON,
#      causing truncation → JSONDecodeError → severity=UNKNOWN
#   2. max_output_tokens raised to 2048 (from config) as a safety net
#   3. 429 retry-with-backoff — waits the retry delay from the error
#      message then tries again up to MAX_RETRIES times before giving up
#   4. In-memory cache keyed by chg_number — skips the LLM entirely on
#      re-runs within the same Streamlit session
#   5. Rate-limit delay guard before the API call

import json
import re
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from core.impact_graph import graph_to_text
from config import GEMINI_API_KEY, GEMINI_MODEL, IMPACT_MAX_TOKENS, LLM_CALL_DELAY_SEC

# ── In-memory cache (lives for the life of the Streamlit process) ─
_ANALYSIS_CACHE: dict = {}

# ── How many times to retry on a 429 before giving up ─────────────
MAX_RETRIES = 3


def analyze_impact(change_data: dict, classified_cis: dict, graph: dict) -> dict:
    chg = change_data.get("chg_number", "")

    # ── Cache hit: skip the LLM call entirely ─────────────────────
    if chg and chg in _ANALYSIS_CACHE:
        print(f"[ImpactAnalyzer] ✓ Cache hit for {chg} — skipping LLM call")
        return _ANALYSIS_CACHE[chg]

    prod_names    = [ci["name"] for ci in classified_cis.get("prod",    [])]
    dr_names      = [ci["name"] for ci in classified_cis.get("dr",      [])]
    nonprod_names = [ci["name"] for ci in classified_cis.get("nonprod", [])]

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

    # ── Rate limit guard ───────────────────────────────────────────
    if LLM_CALL_DELAY_SEC > 0:
        print(f"[ImpactAnalyzer] Waiting {LLM_CALL_DELAY_SEC}s (rate limit guard)...")
        time.sleep(LLM_CALL_DELAY_SEC)

    # FIX 1: thinking_budget=0 — this is the primary fix for truncated JSON.
    # Both gemini-2.5-flash and gemini-2.5-flash-lite are thinking models.
    # By default they allocate up to 8 192 thinking tokens which count against
    # max_output_tokens.  Disabling thinking is correct for this task: the
    # prompt is deterministic structured-output, not a reasoning problem.
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
        max_output_tokens=IMPACT_MAX_TOKENS,
        model_kwargs={
            "generation_config": {
                "thinking_config": {"thinking_budget": 0}
            }
        },
    )
    chain = llm | StrOutputParser()

    # FIX 3: retry loop with 429-aware backoff ─────────────────────
    result     = None
    last_exc   = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = chain.invoke(prompt)
            break   # success — exit retry loop
        except Exception as e:
            last_exc = e
            err_str  = str(e)

            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                # Parse the suggested retry delay from the error message.
                # The API returns e.g. "Please retry in 47.914816772s"
                match    = re.search(r'retry in (\d+)', err_str)
                wait_sec = int(match.group(1)) + 5 if match else 60
                print(
                    f"[ImpactAnalyzer] ⚠ 429 RESOURCE_EXHAUSTED "
                    f"(attempt {attempt}/{MAX_RETRIES}) — "
                    f"waiting {wait_sec}s then retrying..."
                )
                if attempt < MAX_RETRIES:
                    time.sleep(wait_sec)
                # else: fall through to raise below
            else:
                # Non-quota error (auth failure, network issue, etc.)
                # — raise immediately, no point retrying
                raise

    if result is None:
        # All retries exhausted — surface a clear, actionable error
        raise RuntimeError(
            f"[ImpactAnalyzer] Gemini API quota exhausted after {MAX_RETRIES} retries "
            f"for {chg}. Free-tier limit: 20 req/day for gemini-2.5-flash, "
            f"1000 req/day for gemini-2.5-flash-lite. "
            f"Set GEMINI_MODEL=gemini-2.5-flash-lite in your .env to get 50× more headroom. "
            f"Original error: {last_exc}"
        )

    # ── Parse JSON response ────────────────────────────────────────
    try:
        clean  = result.strip().replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        # Log the raw response so truncation is visible in the terminal
        print(f"[ImpactAnalyzer] ⚠ JSONDecodeError — raw response was:\n{result!r}")
        parsed = {"severity": "UNKNOWN", "risk_summary": result}

    parsed["raw_llm_response"] = result
    parsed.setdefault("prod_ci_count",    len(prod_names))
    parsed.setdefault("dr_ci_count",      len(dr_names))
    parsed.setdefault("nonprod_ci_count", len(nonprod_names))

    # ── Store in cache ─────────────────────────────────────────────
    if chg:
        _ANALYSIS_CACHE[chg] = parsed

    print(f"[ImpactAnalyzer] ✓ Severity: {parsed.get('severity')}")
    return parsed