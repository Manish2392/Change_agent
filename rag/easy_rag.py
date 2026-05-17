# rag/easy_rag.py — EasyRAG with FAISS (updated for new LangChain)
import os
import json
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from config import GEMINI_API_KEY, FAISS_INDEX_PATH, RAG_TOP_K


class EasyRAG:
    def __init__(self):
        self.embeddings  = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=GEMINI_API_KEY,
        )
        self.index_path  = FAISS_INDEX_PATH
        self.vectorstore = self._load_or_create()

    def ingest(self, report: dict):
        chg_number = report.get("meta", {}).get("chg_number", "UNKNOWN")
        text       = self._report_to_text(report)
        doc = Document(
            page_content=text,
            metadata={
                "chg_number": chg_number,
                "severity":   report.get("impact", {}).get("severity", ""),
                "category":   report.get("change", {}).get("category", ""),
            }
        )
        self.vectorstore.add_documents([doc])
        self._save()
        print(f"[EasyRAG] ✓ Ingested {chg_number}")

    def retrieve(self, change_data: dict) -> str:
        query = (
            f"Change: {change_data.get('description', '')} "
            f"Category: {change_data.get('category', '')} "
            f"Risk: {change_data.get('risk', '')}"
        )
        try:
            docs = self.vectorstore.similarity_search(query, k=RAG_TOP_K)
        except Exception:
            return "(No historical data available yet)"

        if not docs:
            return "(No similar past changes found)"

        lines = [f"=== {len(docs)} Similar Historical Changes ==="]
        for i, doc in enumerate(docs, 1):
            lines.append(f"\n--- Past Change #{i} ---")
            lines.append(doc.page_content)
        return "\n".join(lines)

    def get_stats(self) -> dict:
        try:
            count = self.vectorstore.index.ntotal
        except Exception:
            count = 0
        return {"indexed_changes": count, "index_path": self.index_path}

    def _load_or_create(self) -> FAISS:
        if os.path.exists(self.index_path):
            print(f"[EasyRAG] Loading existing FAISS index")
            return FAISS.load_local(
                self.index_path,
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
        print("[EasyRAG] Creating new FAISS index")
        placeholder = Document(
            page_content="FlowMaster RAG index initialised.",
            metadata={"chg_number": "INIT"}
        )
        store = FAISS.from_documents([placeholder], self.embeddings)
        os.makedirs(self.index_path, exist_ok=True)
        store.save_local(self.index_path)
        return store

    def _save(self):
        os.makedirs(self.index_path, exist_ok=True)
        self.vectorstore.save_local(self.index_path)

    def _report_to_text(self, report: dict) -> str:
        change  = report.get("change", {})
        summary = report.get("ci_summary", {})
        impact  = report.get("impact", {})
        return (
            f"CHG: {change.get('chg_number')} | "
            f"Category: {change.get('category')} | "
            f"Desc: {change.get('description')} | "
            f"Risk: {change.get('risk')} | "
            f"Severity: {impact.get('severity')} | "
            f"Downtime: {impact.get('estimated_downtime_minutes')} min | "
            f"PROD CIs: {summary.get('PROD', 0)} | "
            f"Services: {', '.join(impact.get('affected_business_services', []))}"
        )