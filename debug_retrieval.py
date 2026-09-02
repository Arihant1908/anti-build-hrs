import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import warnings
warnings.filterwarnings("ignore")
import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.PersistentClient(path="data/chroma_db")
col = client.get_collection("groww_funds")
model = SentenceTransformer("all-MiniLM-L6-v2")

query = "What is the expense ratio of HDFC Large Cap Fund?"
emb = model.encode(query).tolist()
results = col.query(query_embeddings=[emb], n_results=5)

print("Query:", query)
print()
for i in range(len(results["ids"][0])):
    d = results["distances"][0][i]
    meta = results["metadatas"][0][i]
    text = results["documents"][0][i][:200].encode("ascii", errors="replace").decode("ascii")
    fund = meta["fund_name"]
    cat = meta["fund_category"]
    print(f"[{i+1}] Distance: {d:.4f} | Fund: {fund} | Category: {cat}")
    print(f"    Text: {text}...")
    print()

# Also check: what Large Cap chunks contain "expense ratio"?
print("=" * 50)
print("Large Cap chunks containing 'expense':")
all_data = col.get(where={"fund_category": "Large Cap"})
for i, doc in enumerate(all_data["documents"]):
    if "expense" in doc.lower() or "Expense" in doc:
        preview = doc[:200].encode("ascii", errors="replace").decode("ascii")
        print(f"  ID: {all_data['ids'][i]}")
        print(f"  Text: {preview}...")
        print()
