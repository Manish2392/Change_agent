# config.py — All settings and environment variables
import os
from dotenv import load_dotenv

load_dotenv()

# ── ServiceNow ─────────────────────────────────────────────
SNOW_INSTANCE  = os.getenv("SNOW_INSTANCE",  "https://your-company.service-now.com")
SNOW_USERNAME  = os.getenv("SNOW_USERNAME",  "your_username")
SNOW_PASSWORD  = os.getenv("SNOW_PASSWORD",  "your_password")

# ── Mock mode ──────────────────────────────────────────────
# Set USE_MOCK_SERVICENOW=true in your .env to run without real SNOW credentials.
# Pipeline and chatbot behave identically — only the data source changes.
USE_MOCK_SERVICENOW = os.getenv("USE_MOCK_SERVICENOW", "true").lower() == "true"

# ── Google Gemini ───────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_gemini_api_key")
GEMINI_MODEL = "gemini-2.5-flash"

# ── LangChain ──────────────────────────────────────────────
LANGCHAIN_VERBOSE = False                    # Set True for debug traces

# ── RAG / FAISS ────────────────────────────────────────────
FAISS_INDEX_PATH   = "./rag/faiss_index"
EMBEDDING_MODEL    = "models/gemini-embedding-001"
RAG_TOP_K          = 3

# ── Pipeline ───────────────────────────────────────────────
MAX_CI_DEPTH = 3

# ── Environment classification keywords ────────────────────
PROD_ENVS    = ["prod", "production", "prd"]
DR_ENVS      = ["dr", "disaster-recovery", "disaster_recovery"]
NONPROD_ENVS = ["dev", "qa", "uat", "staging", "test", "non-prod", "nonprod"]
