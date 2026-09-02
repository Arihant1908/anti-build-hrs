"""
Phase 3 & 4 — Embedding and Vector Store
Converts TextChunks into embeddings and stores them in ChromaDB.

Architecture reference: docs/architecture.md § Phase 3, Phase 4
PRD reference: docs/PRD.md § 4.3, § 4.4
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any

import chromadb
from sentence_transformers import SentenceTransformer

# Import TextChunk from chunker
from src.ingestion.chunker import TextChunk, CHUNKS_DATA_DIR

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("embedder")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "groww_funds"

CHROMA_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "chroma_db"

# ---------------------------------------------------------------------------
# Loading Chunks
# ---------------------------------------------------------------------------
def load_all_chunks(chunks_dir: Path = CHUNKS_DATA_DIR) -> List[TextChunk]:
    """Loads all TextChunks from the data/chunks/ directory."""
    chunks = []
    manifest_path = chunks_dir / "chunk_manifest.json"
    
    if not manifest_path.exists():
        logger.warning(f"Manifest not found at {manifest_path}. Loading all JSON files directly.")
        json_files = list(chunks_dir.glob("*_chunks.json"))
    else:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        json_files = [chunks_dir / fname for fname in manifest.get("files", [])]

    for filepath in json_files:
        if not filepath.exists():
            logger.error(f"Chunk file listed in manifest not found: {filepath}")
            continue
            
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                chunks.append(TextChunk(**item))
                
    logger.info(f"Loaded {len(chunks)} chunks from {len(json_files)} files.")
    return chunks

# ---------------------------------------------------------------------------
# Embedder Logic
# ---------------------------------------------------------------------------
class FundEmbedder:
    """Handles embedding generation and ChromaDB storage."""
    
    def __init__(self, db_path: Path = CHROMA_DB_DIR, model_name: str = MODEL_NAME):
        self.model_name = model_name
        
        logger.info(f"Loading embedding model '{self.model_name}' (CPU)...")
        self.model = SentenceTransformer(self.model_name)
        
        logger.info(f"Initializing ChromaDB client at {db_path}...")
        db_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(db_path))
        
        # We explicitly set space to 'cosine' as specified in architecture
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Connected to collection '{COLLECTION_NAME}' (cosine similarity).")

    def embed_and_store(self, chunks: List[TextChunk]) -> None:
        """
        Computes embeddings for all chunks and upserts them into ChromaDB.
        """
        if not chunks:
            logger.warning("No chunks provided to embed_and_store.")
            return

        logger.info(f"Encoding {len(chunks)} chunks...")
        
        texts = [chunk.text for chunk in chunks]
        
        # model.encode supports batching natively
        embeddings = self.model.encode(texts, show_progress_bar=True)
        # Convert embeddings to lists of floats
        embeddings_list = [emb.tolist() for emb in embeddings]
        
        logger.info(f"Upserting {len(chunks)} vectors to ChromaDB...")
        
        ids = [chunk.chunk_id for chunk in chunks]
        
        # Build metadata for each chunk
        metadatas = []
        for chunk in chunks:
            metadatas.append({
                "source_url": chunk.source_url,
                "fund_name": chunk.fund_name,
                "fund_category": chunk.fund_category,
                "scrape_timestamp": chunk.scrape_timestamp,
                "chunk_index": chunk.chunk_index
            })

        # Upsert in batches to avoid any ChromaDB limits if there were many chunks
        # With ~200 chunks, a single batch is perfectly fine.
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings_list,
            documents=texts,
            metadatas=metadatas
        )
        
        logger.info("Upsert complete.")
        logger.info(f"Total documents in collection '{COLLECTION_NAME}': {self.collection.count()}")

# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------
def run_embedding() -> None:
    """
    Execute Phase 3 & 4:
    1. Load all TextChunks
    2. Embed using SentenceTransformer
    3. Store in ChromaDB
    """
    logger.info(
        f"\n{'-'*60}\n"
        f"PHASE 3 & 4 — EMBEDDING & VECTOR STORE\n"
        f"{'-'*60}"
    )
    
    chunks = load_all_chunks()
    if not chunks:
        logger.error("No chunks found. Please run Phase 2 first.")
        return
        
    embedder = FundEmbedder()
    embedder.embed_and_store(chunks)
    
    logger.info(
        f"\n{'-'*60}\n"
        f"PHASE 3 & 4 COMPLETE\n"
        f"  Model: {MODEL_NAME}\n"
        f"  Total Vectors: {len(chunks)}\n"
        f"  Vector DB: {CHROMA_DB_DIR}\n"
        f"{'-'*60}\n"
    )

if __name__ == "__main__":
    run_embedding()
