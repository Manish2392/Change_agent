# test_rag.py — Ingest all saved reports into FAISS RAG
import json
import os
from rag.easy_rag import EasyRAG

rag = EasyRAG()

# Load all saved reports and ingest them
reports_dir = "./reports"
if not os.path.exists(reports_dir):
    print("No reports folder found. Run test_run.py first!")
    exit()

files = [f for f in os.listdir(reports_dir) if f.endswith(".json")]
if not files:
    print("No reports found. Run test_run.py first!")
    exit()

print(f"\nIngesting {len(files)} reports into FAISS...\n")

for filename in files:
    with open(f"{reports_dir}/{filename}") as f:
        report = json.load(f)
    chg = report.get("meta", {}).get("chg_number", "?")
    rag.ingest(report)
    print(f"✓ Ingested {chg}")

stats = rag.get_stats()
print(f"""
╔══════════════════════════════════════════╗
║         RAG Ingestion Complete!          ║
╠══════════════════════════════════════════╣
║  Total CHGs in memory : {str(stats['indexed_changes']):<18}║
║  Index location       : ./rag/faiss_index║
╚══════════════════════════════════════════╝
""")