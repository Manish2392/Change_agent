# ⚡ FlowMaster — AI Change Impact Analysis Agent
> HCLTech | GenAI Project | LangChain + Gemini + FAISS + Streamlit

---

## 📁 Project Structure

```
flowmaster/
│
├── app.py                        ← Streamlit UI (run this)
├── main.py                       ← CLI entry point
├── pipeline.py                   ← Orchestrator (chains steps 1→5)
├── ops_copilot.py                ← LangChain ConversationChain Q&A
├── config.py                     ← All settings & API keys
├── requirements.txt
├── .env.example                  ← Copy to .env and fill in keys
│
├── core/                         ← Pipeline steps
│   ├── change_miner.py           ← Step 1: Fetch CHG from ServiceNow
│   ├── ci_mapper.py              ← Step 2: BFS traverse CMDB
│   ├── env_classifier.py         ← Step 3: Classify PROD/DR/NON-PROD
│   ├── impact_graph.py           ← Step 4: Build dependency graph
│   └── impact_analyzer.py        ← Step 5: Gemini LLM + RAG analysis
│
├── rag/
│   ├── easy_rag.py               ← FAISS ingest + retrieval
│   └── faiss_index/              ← Auto-created on first run
│
├── integrations/
│   └── servicenow_client.py      ← ServiceNow REST API wrapper
│
└── reports/                      ← Auto-saved JSON reports
```

---

## 🚀 Setup & Run

```bash
# 1. Clone / download the project
cd flowmaster

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials
cp .env.example .env
# Edit .env with your real ServiceNow + Gemini credentials

# 5. Run Streamlit UI
streamlit run app.py

# OR run CLI
python main.py CHG0012345
python main.py CHG0012345 --no-qa       # skip Q&A
python main.py --load reports/report_CHG0012345.json  # load saved
```

---

## 🔄 Pipeline Flow

```
User enters CHG number
        ↓
[1] ChangeMiner      → Fetch CHG + dates + primary CI from ServiceNow
        ↓
[2] CI Mapper        → BFS traverse CMDB relationships (depth=3)
        ↓
[3] EnvClassifier    → Label each CI: PROD / DR / NON-PROD / UNKNOWN
        ↓
[4] ImpactGraph      → Build nodes + edges dependency graph
        ↓
[5] ImpactAnalyzer   → LangChain + Gemini + FAISS RAG historical context
        ↓
    JSON Report saved to ./reports/
        ↓
[6] RAG Ingest       → Store report in FAISS for future retrievals
        ↓
OpsCopilot           → LangChain ConversationChain for NL Q&A
```

---

## 🧠 RAG (EasyRAG) — How It Works

- Every completed analysis is **embedded and stored in FAISS**
- When a new CHG comes in, the system retrieves the **top-3 most similar past changes**
- This historical context is injected into the Gemini prompt
- Result: better downtime estimates and risk predictions over time

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangChain (LLMChain, ConversationChain) |
| LLM | Google Gemini 1.5 Flash |
| Embeddings | Google `models/embedding-001` |
| Vector DB / RAG | FAISS (local, persistent) |
| Source of Truth | ServiceNow REST API |
| UI | Streamlit + Plotly |
| Language | Python 3.10+ |
