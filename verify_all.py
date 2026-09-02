import os
import json
import chromadb
from pathlib import Path

print("=== VERIFYING PHASE 1: DATA LOADING (Raw Data) ===")
raw_dir = Path("data/raw")
if raw_dir.exists():
    raw_files = list(raw_dir.glob("*.json"))
    print(f"Found {len(raw_files)} raw data files.")
    for f in raw_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                print(f"  - {f.name}: Fund = '{data.get('fund_name')}', Text length = {len(data.get('raw_text', ''))} chars")
        except Exception as e:
            print(f"  - {f.name}: Error reading file - {e}")
else:
    print("Directory data/raw does not exist.")

print("\n=== VERIFYING PHASE 2: CHUNKING (Chunked Data) ===")
chunks_dir = Path("data/chunks")
total_chunks_saved = 0
if chunks_dir.exists():
    chunk_files = list(chunks_dir.glob("*.json"))
    print(f"Found {len(chunk_files)} chunk files.")
    for f in chunk_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                chunks_in_file = len(data)
                total_chunks_saved += chunks_in_file
                print(f"  - {f.name}: Contains {chunks_in_file} chunks")
        except Exception as e:
            print(f"  - {f.name}: Error reading file - {e}")
    print(f"Total chunks saved to disk: {total_chunks_saved}")
else:
    print("Directory data/chunks does not exist.")

print("\n=== VERIFYING PHASE 3 & 4: EMBEDDING & VECTOR STORE (ChromaDB) ===")
try:
    client = chromadb.PersistentClient(path="data/chroma_db")
    col = client.get_collection("groww_funds")
    count = col.count()
    print(f"Successfully connected to ChromaDB at 'data/chroma_db'")
    print(f"Collection 'groww_funds' exists and contains {count} embedded documents.")
    
    if count > 0:
        # Peek at one document to verify embeddings and metadata
        peek = col.peek(1)
        has_embeddings = peek.get('embeddings') is not None and len(peek['embeddings']) > 0
        has_metadata = peek.get('metadatas') is not None and len(peek['metadatas']) > 0
        print(f"  - Vector embeddings present: {'Yes' if has_embeddings else 'No'}")
        print(f"  - Metadata present: {'Yes' if has_metadata else 'No'}")
        if has_metadata:
            print(f"  - Sample metadata keys: {list(peek['metadatas'][0].keys())}")
            
    if count == total_chunks_saved and count > 0:
        print("\n✅ SUCCESS: The number of chunks in ChromaDB matches the number of saved chunks!")
    else:
        print(f"\n⚠️ WARNING: ChromaDB has {count} documents, but we saved {total_chunks_saved} chunks to disk.")
        
except Exception as e:
    print(f"Error accessing ChromaDB: {e}")
