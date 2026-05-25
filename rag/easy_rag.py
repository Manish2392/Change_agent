# rag/easy_rag.py — FAISS RAG with self-exclusion and rich query matching
import os
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
                "chg_number":  chg_number,
                "severity":    report.get("impact", {}).get("severity", ""),
                "category":    report.get("change", {}).get("category", ""),
                "environment": report.get("change", {}).get("environment", ""),
            }
        )
        self.vectorstore.add_documents([doc])
        self._save()
        print(f"  [ingested] {chg_number}")

    def retrieve(self, report: dict) -> str:
        """
        Retrieve similar past changes from FAISS.
        Accepts the FULL report dict (not just report[change]).

        FIX 1 — self-exclusion:
            Fetch RAG_TOP_K + 3 results then filter out the current CHG.
            Without this FAISS returns the current change as top match.

        FIX 2 — richer query:
            Query mirrors the richness of stored vectors for better matching.

        FIX 3 — correct dict access:
            report[change][impact] is a string ("Critical").
            report[impact] is the dict with severity/services/etc.
            We now correctly read from both sub-dicts separately.
        """
        change      = report.get("change", {})
        impact      = report.get("impact", {})   # FIX 3: top-level impact dict
        current_chg = change.get("chg_number", "")
        services    = ", ".join(impact.get("affected_business_services", []))

        # FIX 2: rich query matches the richness of stored vectors
        query = (
            f"Category: {change.get('category', '')} "
            f"Risk: {change.get('risk', '')} "
            f"Environment: {change.get('environment', '')} "
            f"Description: {change.get('description', '')} "
            f"Severity: {impact.get('severity', '')} "
            f"Affected services: {services}"
        )

        try:
            # FIX 1: fetch extra results so we have enough after filtering self
            docs = self.vectorstore.similarity_search(query, k=RAG_TOP_K + 3)
        except Exception as e:
            print(f"[EasyRAG] similarity_search failed: {type(e).__name__}: {e}")
            return "(No historical data available yet)"

        # FIX 1: remove the current CHG from results
        if current_chg:
            docs = [
                d for d in docs
                if d.metadata.get("chg_number") != current_chg
            ]

        # trim to RAG_TOP_K after filtering
        docs = docs[:RAG_TOP_K]

        if not docs:
            return "(No similar past changes found)"

        lines = [f"=== {len(docs)} Similar Historical Changes ==="]
        for i, doc in enumerate(docs, 1):
            chg  = doc.metadata.get("chg_number", "Unknown")
            cat  = doc.metadata.get("category", "")
            sev  = doc.metadata.get("severity", "")
            lines.append(f"\n--- Past Change #{i} ({chg} | {cat} | {sev}) ---")
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
            print(f"[EasyRAG] Loading existing FAISS index from {self.index_path}")
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
        change   = report.get("change", {})
        summary  = report.get("ci_summary", {})
        impact   = report.get("impact", {})
        failures = impact.get("potential_failures", [])
        recs     = impact.get("recommendations", [])
        services = impact.get("affected_business_services", [])

        return (
            f"Change: {change.get('chg_number')} | "
            f"Category: {change.get('category')} | "
            f"Environment: {change.get('environment', 'Production')} | "
            f"Description: {change.get('description')} | "
            f"Risk: {change.get('risk')} | Impact: {change.get('impact')} | "
            f"State: {change.get('state')} | "
            f"Severity: {impact.get('severity')} | "
            f"Downtime: {impact.get('estimated_downtime_minutes')} minutes | "
            f"Rollback complexity: {impact.get('rollback_complexity')} | "
            f"PROD CIs: {summary.get('PROD', 0)} | "
            f"DR CIs: {summary.get('DR', 0)} | "
            f"NonProd CIs: {summary.get('NON-PROD', 0)} | "
            f"Affected services: {', '.join(services)} | "
            f"Risk summary: {impact.get('risk_summary', '')} | "
            f"Potential failures: {'; '.join(failures)} | "
            f"Recommendations: {'; '.join(recs)}"
        )