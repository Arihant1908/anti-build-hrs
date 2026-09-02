import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import chromadb

client = chromadb.PersistentClient(path="data/chroma_db")
col = client.get_collection("groww_funds")

print("=" * 50)
print("  VECTOR DB VERIFICATION REPORT")
print("=" * 50)
print()
print(f"  Total documents stored: {col.count()}")
print(f"  Collection name: groww_funds")
print(f"  DB path: data/chroma_db/")
print()

# Get a sample to verify structure
sample = col.peek(3)
ids = sample["ids"]
metas = sample["metadatas"]
docs = sample["documents"]

print("  --- Sample Documents ---")
for i in range(len(ids)):
    print(f"  [{i+1}] ID: {ids[i]}")
    print(f"      Fund: {metas[i]['fund_name']}")
    print(f"      Category: {metas[i]['fund_category']}")
    print(f"      URL: {metas[i]['source_url']}")
    preview = docs[i][:80].encode("ascii", errors="replace").decode("ascii")
    print(f"      Text preview: {preview}...")
    print()

# Count per fund category
all_meta = col.get()["metadatas"]
categories = {}
for m in all_meta:
    cat = m.get("fund_category", "Unknown")
    categories[cat] = categories.get(cat, 0) + 1

print("  --- Chunks Per Fund Category ---")
for cat, count in sorted(categories.items()):
    print(f"    {cat}: {count} chunks")

# Quick similarity test (no LLM needed)
print()
print("  --- Quick Similarity Search Test ---")
from sentence_transformers import SentenceTransformer
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
model = SentenceTransformer("all-MiniLM-L6-v2")
test_query = "expense ratio"
emb = model.encode(test_query).tolist()
results = col.query(query_embeddings=[emb], n_results=3)
print(f"  Query: '{test_query}'")
print(f"  Top 3 results:")
for i in range(len(results["ids"][0])):
    dist = results["distances"][0][i]
    fund = results["metadatas"][0][i]["fund_name"]
    text = results["documents"][0][i][:60].encode("ascii", errors="replace").decode("ascii")
    print(f"    [{i+1}] Distance: {dist:.4f} | Fund: {fund}")
    print(f"        Text: {text}...")

print()
print("  Persistence: YES (PersistentClient on disk)")
print("=" * 50)
