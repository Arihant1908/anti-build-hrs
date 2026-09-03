import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from dataclasses import dataclass
from typing import List, Dict, Tuple
import chromadb
from sentence_transformers import SentenceTransformer

from src.guardrails.pii_filter import PIIFilter
from src.guardrails.intent_classifier import IntentClassifier
from src.retrieval.prompt_builder import PromptBuilder
from src.generation.llm_client import LLMClient

@dataclass
class RetrievalResult:
    answer: str
    chunks: List[Dict] = None
    distances: List[float] = None
    metadatas: List[Dict] = None
    blocked: bool = False
    block_reason: str = None

class RAGRetriever:
    """
    Orchestrates the retrieval and generation pipeline.
    """
    def __init__(self, db_path: str = None):
        self.pii_filter = PIIFilter()
        self.intent_classifier = IntentClassifier()
        self.prompt_builder = PromptBuilder()
        self.llm_client = LLMClient()
        
        # We need the same model used for embedding
        self.model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        print(f"Loading query embedding model '{self.model_name}'...")
        self.encoder = SentenceTransformer(self.model_name)
        
        # Connect to ChromaDB — resolve path relative to project root
        if db_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(project_root, "data", "chroma_db")
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.collection = self.chroma_client.get_collection(name="groww_funds")
        
        # Configs
        self.top_k = int(os.getenv("RETRIEVAL_TOP_K", "3"))
        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))

    # Known fund names and their ChromaDB category values
    FUND_MAP = {
        "large cap": "Large Cap",
        "flexi cap": "Flexi Cap",
        "elss": "ELSS",
        "tax saver": "ELSS",
        "small cap": "Small Cap",
        "balanced advantage": "Hybrid",
        "balanced": "Hybrid",
    }

    def _detect_fund_category(self, query: str) -> str:
        """Detect which fund category the user is asking about."""
        query_lower = query.lower()
        for keyword, category in self.FUND_MAP.items():
            if keyword in query_lower:
                return category
        return None

    def process_query(self, query: str) -> RetrievalResult:
        """
        End-to-end processing of a user query.
        """
        # 1. Guardrails
        has_pii, pii_reason = self.pii_filter.check_pii(query)
        if has_pii:
            return RetrievalResult(answer=pii_reason, blocked=True, block_reason="PII Detected")
            
        is_blocked, intent_reason = self.intent_classifier.classify_intent(query)
        if is_blocked:
            return RetrievalResult(answer=intent_reason, blocked=True, block_reason="Restricted Intent")

        # 2. Embed Query
        query_embedding = self.encoder.encode(query).tolist()
        
        # 3. ChromaDB Query — general semantic search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=self.top_k
        )
        
        chunks = list(results['documents'][0])
        distances = list(results['distances'][0])
        metadatas = list(results['metadatas'][0])

        # 3b. If a specific fund is mentioned, also do a targeted search
        #     filtered to that fund's chunks. We fetch more chunks here (10)
        #     because data-dense chunks (like expense ratio) often have worse 
        #     semantic scores than verbose descriptive text.
        detected_category = self._detect_fund_category(query)
        if detected_category:
            filtered_results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=30,  # Fetch ALL chunks for the fund to ensure we don't miss data tables
                where={"fund_category": detected_category}
            )
            existing_texts = set(chunks)
            for i in range(len(filtered_results['documents'][0])):
                doc = filtered_results['documents'][0][i]
                if doc not in existing_texts:
                    chunks.append(doc)
                    distances.append(filtered_results['distances'][0][i])
                    metadatas.append(filtered_results['metadatas'][0][i])
                    existing_texts.add(doc)

        # 4. Relevance Check & Keyword Boosting
        # We give a significant distance reduction (boost) to chunks that 
        # contain exact keywords from the query (like "expense", "load", "sip")
        max_distance_allowed = 1.0 - self.similarity_threshold
        
        scored_chunks = []
        for dist, chunk, meta in zip(distances, chunks, metadatas):
            chunk_text_lower = chunk.lower()
            query_lower = query.lower()
            
            # 1. Single term boosting
            query_terms = set(word.strip("?.,\"'") for word in query_lower.split())
            boost = 0.0
            for term in query_terms:
                if len(term) > 3 and term in chunk_text_lower:
                    boost += 0.05
                    
            # 2. Strong keyphrase boosting
            strong_phrases = ["expense ratio", "nav", "exit load", "aum", "fund size", "minimum sip", "minimum lumpsum"]
            for phrase in strong_phrases:
                if phrase in query_lower and phrase in chunk_text_lower:
                    boost += 0.3  # Huge boost for exact matching critical data points
                    
            adjusted_distance = max(0.0, dist - boost)
            scored_chunks.append((adjusted_distance, chunk, meta))
            
        scored_chunks.sort(key=lambda x: x[0])
        
        valid_chunks = []
        valid_metadatas = []
        valid_distances = []
        
        # Take the top K after boosting, if they pass the threshold
        for dist, chunk, meta in scored_chunks:
            if dist <= max_distance_allowed:
                valid_chunks.append(chunk)
                valid_metadatas.append(meta)
                valid_distances.append(dist)
                if len(valid_chunks) >= self.top_k:
                    break
                
        if not valid_chunks:
            return RetrievalResult(
                answer="I couldn't find relevant information in the HDFC Mutual Fund FAQs to answer your question.",
                blocked=False
            )
            
        # 5. Build Prompt
        prompt = self.prompt_builder.build_prompt(query, valid_chunks, valid_metadatas)
        
        # 6. Generate Answer
        answer = self.llm_client.generate_answer(prompt)
        
        return RetrievalResult(
            answer=answer,
            chunks=valid_chunks,
            distances=valid_distances,
            metadatas=valid_metadatas
        )

# Simple CLI test wrapper if executed directly
if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    
    retriever = RAGRetriever()
    print("\n" + "=" * 50)
    print("  HDFC Mutual Fund RAG Chatbot — Test Mode")
    print("=" * 50)
    print("  Type your question and press Enter.")
    print("  Type 'exit' to quit.\n")
    
    while True:
        try:
            q = input("Query: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        
        if not q:
            continue  # Skip empty input silently
        
        if q.lower() in ['exit', 'quit']:
            print("Goodbye!")
            break
        
        result = retriever.process_query(q)
        print(f"\nAnswer:\n{result.answer}\n")
        print("-" * 50)
