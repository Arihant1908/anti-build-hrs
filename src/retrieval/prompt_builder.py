from typing import List, Dict

class PromptBuilder:
    """
    Assembles the final prompt for the Mistral LLM using retrieved chunks and user query.
    Based on the System Prompt Template from architecture.md (Phase 5).
    """
    
    SYSTEM_TEMPLATE = """You are a facts-only FAQ assistant for HDFC mutual funds on Groww.in.

RULES:
1. Answer ONLY using the context provided below. Do not use outside knowledge.
2. Keep answers to 3 sentences or fewer.
3. Always include the source URL as a citation at the end.
4. Always end with "Last updated from sources: {scrape_date}".
5. If the question asks for investment advice, opinions, or buy/sell
   recommendations, politely refuse and suggest visiting Groww's learning centre.
6. If the question asks about fund returns or performance comparison,
   refuse and link to the official fund factsheet.
7. If you cannot find the answer in the context, say so honestly.

CONTEXT:
{context}

SOURCE URLS:
{source_urls}

USER QUESTION:
{user_query}"""

    def build_prompt(self, query: str, chunks: List[Dict], metadatas: List[Dict]) -> str:
        """
        Builds the prompt by injecting context and metadata.
        """
        # Format context chunks
        context_parts = []
        for i, chunk in enumerate(chunks):
            # Extract just the text from the chunk dict if necessary
            text = chunk if isinstance(chunk, str) else chunk.get("text", "")
            context_parts.append(f"[Chunk {i+1}]: {text}")
            
        context_text = "\n\n".join(context_parts)
        
        # Format source URLs and find latest scrape date
        unique_urls = set()
        scrape_dates = []
        for meta in metadatas:
            if meta and "source_url" in meta:
                unique_urls.add(meta["source_url"])
            if meta and "scrape_timestamp" in meta:
                scrape_dates.append(meta["scrape_timestamp"])
                
        source_urls_text = "\n".join([f"- {url}" for url in unique_urls])
        
        # Use latest scrape date (fallback to today if missing)
        latest_date = max(scrape_dates) if scrape_dates else "Unknown Date"
        
        # Assemble final prompt
        prompt = self.SYSTEM_TEMPLATE.format(
            scrape_date=latest_date,
            context=context_text,
            source_urls=source_urls_text,
            user_query=query
        )
        
        return prompt
