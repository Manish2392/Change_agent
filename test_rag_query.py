# test_rag_query.py — Test if RAG finds similar past changes
from rag.easy_rag import EasyRAG

rag = EasyRAG()

# Simulate a NEW incoming change
new_change = {
    "description": "Apply security patches to production app servers",
    "category":    "Patching",
    "risk":        "Medium",
    "environment": "Production"
}

print("\n🔍 Searching for similar past changes...\n")
print(f"New Change: {new_change['description']}")
print(f"Category  : {new_change['category']}")
print(f"Risk      : {new_change['risk']}")
print("\n" + "="*60)

result = rag.retrieve(new_change)
print(result)
print("="*60)
print("\n✓ RAG retrieval complete!")
print("This context gets sent to Gemini along with every new question.")