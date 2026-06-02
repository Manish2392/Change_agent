# config.py
import os
from dotenv import load_dotenv
load_dotenv()

SNOW_INSTANCE        = os.getenv("SNOW_INSTANCE",  "https://your-company.service-now.com")
SNOW_USERNAME        = os.getenv("SNOW_USERNAME",  "your_username")
SNOW_PASSWORD        = os.getenv("SNOW_PASSWORD",  "your_password")
USE_MOCK_SERVICENOW  = os.getenv("USE_MOCK_SERVICENOW", "true").lower() == "true"

GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY", "your_gemini_api_key")

# ── Model selection ───────────────────────────────────────────
# FIX: Default changed from gemini-2.5-flash → gemini-2.5-flash-lite
#
# Free-tier daily limits (generate_content calls):
#   gemini-2.5-flash      →    20 RPD  ← you were hitting this
#   gemini-2.5-flash-lite →  1000 RPD  ← 50× more headroom
#
# gemini-2.5-flash-lite is still a thinking model with strong structured-
# output quality — more than sufficient for the impact analysis JSON task.
# Switch back to gemini-2.5-flash in .env when you move to a paid plan.
GEMINI_MODEL         = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

# ── Token caps ────────────────────────────────────────────────
# Raised from 400 → 2048: gemini-2.5-flash-lite is also a thinking model
# so the same thinking_budget=0 fix in impact_analyzer.py applies here.
# 2048 gives ample room for the JSON response.
IMPACT_MAX_TOKENS    = int(os.getenv("IMPACT_MAX_TOKENS", "2048"))
CHAT_MAX_TOKENS      = int(os.getenv("CHAT_MAX_TOKENS",   "512"))

# ── Rate limit guard — seconds between LLM calls ─────────────
# gemini-2.5-flash-lite = 15 RPM → 1 call per 5s is safe
# (was 7s for flash; reduced slightly since lite has higher RPM)
LLM_CALL_DELAY_SEC   = float(os.getenv("LLM_CALL_DELAY_SEC", "5"))

LANGCHAIN_VERBOSE    = False
FAISS_INDEX_PATH     = "./rag/faiss_index"
EMBEDDING_MODEL      = "models/gemini-embedding-001"
RAG_TOP_K            = int(os.getenv("RAG_TOP_K", "2"))
MAX_CI_DEPTH         = 3

PROD_ENVS    = ["prod", "production", "prd"]
DR_ENVS      = ["dr", "disaster-recovery", "disaster_recovery"]
NONPROD_ENVS = ["dev", "qa", "uat", "staging", "test", "non-prod", "nonprod"]

# ── Keywords that trigger RAG history lookup ──────────────────
# RAG only fires when user explicitly asks about history/past/similar
RAG_TRIGGER_KEYWORDS = [
    "similar", "past", "previous", "before", "history", "historic",
    "last time", "before this", "other change", "comparison",
    "pattern", "trend", "happened before", "similar change",
    "have we done", "did we do",
]