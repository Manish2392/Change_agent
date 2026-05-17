# config.py — All settings and environment variables
import os
from dotenv import load_dotenv

load_dotenv()

# ── ServiceNow ─────────────────────────────────────────────
SNOW_INSTANCE  = os.getenv("SNOW_INSTANCE",  "https://your-company.service-now.com")
SNOW_USERNAME  = os.getenv("SNOW_USERNAME",  "your_username")
SNOW_PASSWORD  = os.getenv("SNOW_PASSWORD",  "your_password")

# ── Google Gemini ───────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_gemini_api_key")
GEMINI_MODEL = "gemini-2.5-flash"   # or gemini-1.5-latest

# ── LangChain ──────────────────────────────────────────────
LANGCHAIN_VERBOSE = False                    # Set True for debug traces

# ── RAG / FAISS ────────────────────────────────────────────
FAISS_INDEX_PATH   = "./rag/faiss_index"     # Where FAISS index is persisted
EMBEDDING_MODEL = "models/gemini-embedding-001" # Google embedding model
RAG_TOP_K          = 3                       # How many similar past CHGs to retrieve

# ── Pipeline ───────────────────────────────────────────────
MAX_CI_DEPTH = 3                             # CMDB traversal depth

# ── Environment classification keywords ────────────────────
PROD_ENVS    = ["prod", "production", "prd"]
DR_ENVS      = ["dr", "disaster-recovery", "disaster_recovery"]
NONPROD_ENVS = ["dev", "qa", "uat", "staging", "test", "non-prod", "nonprod"]
 