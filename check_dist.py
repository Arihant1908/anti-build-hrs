import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.PersistentClient(path='data/chroma_db')
col = client.get_collection('groww_funds')
encoder = SentenceTransformer('all-MiniLM-L6-v2')

query = "What is the expense ratio of HDFC Large Cap Fund?"
query_emb = encoder.encode(query).tolist()

results = col.query(
    query_embeddings=[query_emb],
    n_results=30,
    where={"fund_category": "Large Cap"}
)

for i in range(len(results['ids'][0])):
    chunk_id = results['ids'][0][i]
    dist = results['distances'][0][i]
    if chunk_id == 'large_cap_0':
        print(f"RAW DISTANCE OF large_cap_0: {dist}")
        
    if '1.02%' in results['documents'][0][i]:
        print(f"CHUNK WITH 1.02% RAW DISTANCE: {dist}")
