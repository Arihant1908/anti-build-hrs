"""
Phase 2 — Chunking
Splits ScrapedDocument objects into semantically meaningful TextChunk objects.

Architecture reference: docs/architecture.md § Phase 2
PRD reference: docs/PRD.md § 4.2
"""

import logging
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict

from langchain_text_splitters import RecursiveCharacterTextSplitter

# Use the ScrapedDocument from scraper
from src.ingestion.scraper import ScrapedDocument, RAW_DATA_DIR

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("chunker")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CHUNK_SIZE = 400
CHUNK_OVERLAP = 50
MIN_CHUNK_SIZE = 50

SEPARATORS = ["\n\n", "\n", " "]

CHUNKS_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "chunks"

# ---------------------------------------------------------------------------
# Data Model (from architecture.md)
# ---------------------------------------------------------------------------
@dataclass
class TextChunk:
    chunk_id: str             # Unique ID: f"{fund_category}_{chunk_index}"
    text: str                 # The chunk content
    chunk_index: int          # Position within the parent document
    source_url: str           # Inherited metadata
    fund_name: str
    fund_category: str
    scrape_timestamp: str


# ---------------------------------------------------------------------------
# Chunking Logic
# ---------------------------------------------------------------------------
class DocumentChunker:
    """Handles splitting of ScrapedDocuments into TextChunks."""
    
    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.splitter = RecursiveCharacterTextSplitter(
            separators=SEPARATORS,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

    def chunk_document(self, document: ScrapedDocument) -> List[TextChunk]:
        """
        Splits a single ScrapedDocument into a list of TextChunk objects.
        """
        raw_chunks = self.splitter.split_text(document.raw_text)
        
        text_chunks = []
        chunk_idx = 0
        
        category_slug = document.fund_category.lower().replace(" ", "_")
        
        for text in raw_chunks:
            text = text.strip()
            if len(text) < MIN_CHUNK_SIZE:
                continue
                
            chunk_id = f"{category_slug}_{chunk_idx}"
            
            chunk = TextChunk(
                chunk_id=chunk_id,
                text=text,
                chunk_index=chunk_idx,
                source_url=document.url,
                fund_name=document.fund_name,
                fund_category=document.fund_category,
                scrape_timestamp=document.scrape_timestamp
            )
            text_chunks.append(chunk)
            chunk_idx += 1
            
        logger.info(f"Chunked '{document.fund_name}' into {len(text_chunks)} chunks.")
        return text_chunks

# ---------------------------------------------------------------------------
# Loading / Saving
# ---------------------------------------------------------------------------
def load_raw_documents(raw_dir: Path = RAW_DATA_DIR) -> List[ScrapedDocument]:
    """Loads all scraped JSON documents from the data/raw/ directory."""
    documents = []
    manifest_path = raw_dir / "manifest.json"
    
    if not manifest_path.exists():
        logger.warning(f"Manifest not found at {manifest_path}. Loading all JSON files directly.")
        json_files = list(raw_dir.glob("*.json"))
        json_files = [f for f in json_files if f.name != "manifest.json"]
    else:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        json_files = [raw_dir / d["file"] for d in manifest.get("documents", [])]

    for filepath in json_files:
        if not filepath.exists():
            logger.error(f"File listed in manifest not found: {filepath}")
            continue
            
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            doc = ScrapedDocument(**data)
            documents.append(doc)
            
    return documents

def save_chunks(chunks: List[TextChunk], output_dir: Path = CHUNKS_DATA_DIR) -> List[Path]:
    """Saves chunks grouped by fund category into data/chunks/."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Group by category
    grouped_chunks: Dict[str, List[TextChunk]] = {}
    for chunk in chunks:
        slug = chunk.fund_category.lower().replace(" ", "_")
        if slug not in grouped_chunks:
            grouped_chunks[slug] = []
        grouped_chunks[slug].append(chunk)
        
    saved_files = []
    
    for slug, fund_chunks in grouped_chunks.items():
        filepath = output_dir / f"{slug}_chunks.json"
        
        chunks_data = [asdict(c) for c in fund_chunks]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"  \U0001f4be Saved {len(fund_chunks)} chunks to {filepath.name}")
        saved_files.append(filepath)
        
    # Also save a chunk manifest
    manifest = {
        "total_chunks": len(chunks),
        "files": [f.name for f in saved_files]
    }
    manifest_path = output_dir / "chunk_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        
    logger.info(f"  \U0001f4cb Chunk manifest saved: {manifest_path}")
    
    return saved_files

# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------
def run_chunking() -> List[TextChunk]:
    """
    Execute Phase 2:
    1. Load raw ScrapedDocument objects from data/raw/
    2. Chunk them using DocumentChunker
    3. Save TextChunks to data/chunks/
    4. Return all TextChunks for Phase 3
    """
    logger.info(
        f"\n{'-'*60}\n"
        f"PHASE 2 — CHUNKING\n"
        f"{'-'*60}"
    )
    
    documents = load_raw_documents()
    if not documents:
        logger.error("No raw documents found to chunk. Please run Phase 1 first.")
        return []
        
    chunker = DocumentChunker()
    all_chunks = []
    
    for doc in documents:
        chunks = chunker.chunk_document(doc)
        all_chunks.extend(chunks)
        
    saved_files = save_chunks(all_chunks)
    
    logger.info(
        f"\n{'-'*60}\n"
        f"PHASE 2 COMPLETE\n"
        f"  Total Documents: {len(documents)}\n"
        f"  Total Chunks: {len(all_chunks)}\n"
        f"  Saved to: {CHUNKS_DATA_DIR}\n"
        f"  Files: {len(saved_files)} JSON files + manifest\n"
        f"{'-'*60}\n"
    )
    
    return all_chunks

if __name__ == "__main__":
    chunks = run_chunking()
    
    # Print summary
    print(f"\n{'-'*60}")
    print(f"Phase 2 Summary: Created {len(chunks)} chunks")
    print(f"{'-'*60}")
    
    # Show first two chunks as a sample
    for i, chunk in enumerate(chunks[:2]):
        print(f"Sample {i+1} [{chunk.chunk_id}]:")
        safe_text = repr(chunk.text[:100]).encode("ascii", "ignore").decode("ascii")
        print(f"Text (len={len(chunk.text)}): {safe_text}...")
        print()
