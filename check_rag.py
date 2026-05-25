# check_rag.py — Verify RAG is working end to end
from rag.easy_rag import EasyRAG

print("\n" + "="*50)
print("  RAG Health Check")
print("="*50)

# Step 1: Check index
print("\n[1] Checking FAISS index...")
rag   = EasyRAG()
stats = rag.get_stats()
print(f"    Total CHGs in memory : {stats['indexed_changes']}")
print(f"    Index path           : {stats['index_path']}")

if stats['indexed_changes'] == 0:
    print("    ❌ Index is EMPTY — run python test_rag.py first!")
else:
    print(f"    ✓ Index has {stats['indexed_changes']} entries")

# Step 2: Test retrieval
print("\n[2] Testing retrieval...")
test_change = {
    "description": "patch production servers",
    "category":    "Patching",
    "risk":        "Medium",
    "environment": "Production"
}
result = rag.retrieve(test_change)
print(f"\n    Query: '{test_change['description']}'")
print(f"\n    Result:\n{result}")

# Step 3: Check if outcome data exists
print("\n[3] Checking if outcome data is in RAG...")
if "outcome" in result.lower() or "success" in result.lower() or "fail" in result.lower():
    print("    ✓ Outcome data found in RAG!")
else:
    print("    ⚠ No outcome data yet — run record_outcome.py for each CHG")

print("\n" + "="*50)
print("  RAG Check Complete!")
print("="*50 + "\n")