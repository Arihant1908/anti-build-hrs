import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import warnings
warnings.filterwarnings("ignore")

from src.retrieval.retriever import RAGRetriever

retriever = RAGRetriever()
query = "What is the expense ratio of HDFC Large Cap Fund?"
print(f"Query: {query}")

# Manually trigger process_query to see what chunks are selected
result = retriever.process_query(query)

print("\n=== SELECTED CHUNKS ===")
for i, chunk in enumerate(result.chunks):
    print(f"[{i+1}] Distance: {result.distances[i]:.4f} | Fund: {result.metadatas[i]['fund_name']}")
    print(f"Text: {chunk[:200].encode('ascii', 'replace').decode('ascii')}...")
    print("-" * 50)
    
print("\n=== FINAL PROMPT SENT TO LLM ===")
prompt = retriever.prompt_builder.build_prompt(query, result.chunks, result.metadatas)
print(prompt.encode('ascii', 'replace').decode('ascii'))
