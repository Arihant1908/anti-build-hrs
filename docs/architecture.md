# System Architecture
## Groww × HDFC Mutual Fund — RAG FAQ Chatbot Prototype

| Field | Detail |
|---|---|
| **Author** | Senior Architect |
| **Created** | 2026-09-02 |
| **Status** | Draft |
| **Reference** | [PRD.md](file:///c:/Users/ariha/anti%20build%20hrs/docs/PRD.md) |

> This architecture is **strictly scoped to the PRD**. No additional data sources, models, or features beyond what the PRD defines.

---

## Table of Contents

1. [End-to-End Architecture Overview](#1-end-to-end-architecture-overview)
2. [Phase 1 — Data Loading](#2-phase-1--data-loading)
3. [Phase 2 — Chunking](#3-phase-2--chunking)
4. [Phase 3 — Embedding](#4-phase-3--embedding)
5. [Phase 4 — Vector Store](#5-phase-4--vector-store)
6. [Phase 5 — Retrieval Logic](#6-phase-5--retrieval-logic)
7. [Phase 6 — Retrieval Testing](#7-phase-6--retrieval-testing)
8. [Cross-Cutting Concerns](#8-cross-cutting-concerns)
9. [File-to-Phase Mapping](#9-file-to-phase-mapping)
10. [Dependency Graph](#10-dependency-graph)

---

## 1. End-to-End Architecture Overview

```
 ╔══════════════════════════════════════════════════════════════════════════╗
 ║                     OFFLINE INGESTION PIPELINE                         ║
 ║                                                                        ║
 ║  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────────┐  ║
 ║  │ PHASE 1  │    │ PHASE 2  │    │ PHASE 3  │    │     PHASE 4      │  ║
 ║  │   Data   │───►│ Chunking │───►│Embedding │───►│   Vector Store   │  ║
 ║  │ Loading  │    │          │    │          │    │   (ChromaDB)     │  ║
 ║  └──────────┘    └──────────┘    └──────────┘    └──────────────────┘  ║
 ║   scraper.py      chunker.py     embedder.py      embedder.py         ║
 ╚══════════════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════════════╗
 ║                      RUNTIME QUERY PIPELINE                            ║
 ║                                                                        ║
 ║  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────────┐  ║
 ║  │   User   │    │Guardrails│    │ PHASE 5  │    │    LLM Answer    │  ║
 ║  │  Input   │───►│PII+Intent│───►│Retrieval │───►│   Generation     │  ║
 ║  │(Streamlit│    │  Filter  │    │  Logic   │    │   (Mistral)      │  ║
 ║  └──────────┘    └──────────┘    └──────────┘    └──────────────────┘  ║
 ║    app.py      pii_filter.py     retriever.py     llm_client.py       ║
 ║                intent_classifier  prompt_builder                       ║
 ╚══════════════════════════════════════════════════════════════════════════╝

 ╔══════════════════════════════════════════════════════════════════════════╗
 ║                        VALIDATION LAYER                                ║
 ║                                                                        ║
 ║  ┌──────────────────────────────────────────────────────────────────┐  ║
 ║  │                       PHASE 6                                    │  ║
 ║  │                  Retrieval Testing                                │  ║
 ║  │   Unit tests · Integration tests · Accuracy benchmarks           │  ║
 ║  └──────────────────────────────────────────────────────────────────┘  ║
 ║   test_retrieval.py · test_guardrails.py · test_edge_cases.py         ║
 ╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 2. Phase 1 — Data Loading

### Purpose
Scrape raw text content from the **5 scoped Groww URLs** defined in the PRD. No other sources.

### Scope (from PRD §3)

| # | Fund | URL |
|---|---|---|
| 1 | HDFC Large Cap Fund | `groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth` |
| 2 | HDFC Flexi Cap Fund | `groww.in/mutual-funds/hdfc-equity-fund-direct-growth` |
| 3 | HDFC ELSS Tax Saver | `groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth` |
| 4 | HDFC Small Cap Fund | `groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth` |
| 5 | HDFC Balanced Advantage | `groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth` |

### Architecture

```
                          ┌─────────────────┐
                          │   URL Registry   │
                          │  (5 URLs, hard-  │
                          │   coded list)    │
                          └────────┬────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │   HTTP Client    │
                          │  requests +      │
                          │  BeautifulSoup   │
                          └────────┬────────┘
                                   │
                          ┌────────┴────────┐
                          │  Fallback?       │
                          │  JS-rendered?    │
                          └────────┬────────┘
                            Yes    │    No
                           ┌───────┘───────┐
                           ▼               ▼
                    ┌─────────────┐  ┌──────────┐
                    │  Playwright  │  │  BS4     │
                    │  (headless)  │  │  Parser  │
                    └──────┬──────┘  └────┬─────┘
                           │              │
                           └──────┬───────┘
                                  ▼
                          ┌─────────────────┐
                          │  Raw Text +      │
                          │  Metadata        │
                          │  {url, fund_name,│
                          │   category,      │
                          │   scrape_date}   │
                          └─────────────────┘
```

### Component: `src/ingestion/scraper.py`

| Responsibility | Detail |
|---|---|
| **Input** | List of 5 URLs (hard-coded constant) |
| **Output** | List of `ScrapedDocument` objects |
| **HTML cleaning** | Strip nav bars, footers, ads, script/style tags. Retain only fund-specific content. |
| **Metadata tagging** | Each document carries: `url`, `fund_name`, `fund_category`, `scrape_timestamp` |
| **Error handling** | Retry 3× with exponential backoff. Log and skip on persistent failure. |

### Data Model

```python
@dataclass
class ScrapedDocument:
    url: str                  # Source Groww URL
    fund_name: str            # e.g., "HDFC Large Cap Fund Direct Growth"
    fund_category: str        # e.g., "Large Cap"
    raw_text: str             # Cleaned plain text from the page
    scrape_timestamp: str     # ISO-8601 timestamp
```

### Constraints (from PRD §4)
- ❌ No third-party blogs or external sources
- ❌ No app back-end screenshots
- ❌ No PII captured during scraping

---

## 3. Phase 2 — Chunking

### Purpose
Split each `ScrapedDocument` into semantically meaningful, overlapping text chunks optimized for embedding quality and retrieval precision.

### Architecture

```
  ┌──────────────────┐
  │ ScrapedDocument   │
  │ (raw_text ~2-5KB │
  │  per page)        │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │  Section Splitter │◄── Split on headings / semantic boundaries first
  │  (optional pre-   │    (e.g., "Expense Ratio", "Exit Load", "SIP")
  │   processing)     │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │  Recursive Char   │
  │  Text Splitter     │
  │                    │
  │  chunk_size: 400   │
  │  chunk_overlap: 50 │
  │  separators:       │
  │  ["\n\n","\n"," "] │
  └────────┬──────────┘
           │
           ▼
  ┌──────────────────┐
  │  List of Chunks   │
  │  each with:       │
  │  - text           │
  │  - chunk_index    │
  │  - parent metadata│
  └──────────────────┘
```

### Component: `src/ingestion/chunker.py`

| Responsibility | Detail |
|---|---|
| **Input** | `ScrapedDocument` object |
| **Output** | List of `TextChunk` objects |
| **Strategy** | `RecursiveCharacterTextSplitter` (LangChain) or custom equivalent |
| **Chunk size** | 400 characters (≈ 80–100 tokens for MiniLM) |
| **Overlap** | 50 characters — ensures no fact is lost at chunk boundaries |
| **Metadata inheritance** | Each chunk inherits `url`, `fund_name`, `fund_category`, `scrape_timestamp` from its parent document |

### Data Model

```python
@dataclass
class TextChunk:
    chunk_id: str             # Unique ID: f"{fund_category}_{chunk_index}"
    text: str                 # The chunk content
    chunk_index: int          # Position within the parent document
    # Inherited metadata
    source_url: str
    fund_name: str
    fund_category: str
    scrape_timestamp: str
```

### Chunking Rules
| Rule | Rationale |
|---|---|
| Prefer splitting on `\n\n` (paragraph) first | Keeps related facts together (e.g., exit load clause stays intact) |
| Fall back to `\n` (line), then ` ` (space) | Handles dense single-paragraph sections |
| Never split mid-word | Maintains token integrity |
| Minimum chunk size: 50 chars | Avoids noise chunks (headers, footers) |

### Expected Output Volume

| Fund Page | Estimated Raw Text | Estimated Chunks (@ 400 chars) |
|---|---|---|
| Each of 5 pages | ~2,000–5,000 chars | ~5–15 chunks |
| **Total** | ~10,000–25,000 chars | **~25–75 chunks** |

---

## 4. Phase 3 — Embedding

### Purpose
Convert each `TextChunk` into a 384-dimensional dense vector using the `sentence-transformers/all-MiniLM-L6-v2` model (as specified in PRD §6.1).

### Architecture

```
  ┌──────────────────┐
  │  List of          │
  │  TextChunk objects │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────────────────┐
  │  SentenceTransformer         │
  │  Model: all-MiniLM-L6-v2    │
  │                              │
  │  • 384 dimensions            │
  │  • ~22M parameters           │
  │  • Runs on CPU               │
  │  • Max seq length: 256 tokens│
  └────────┬─────────────────────┘
           │
           │  model.encode(chunk.text)
           │
           ▼
  ┌──────────────────┐
  │  EmbeddedChunk    │
  │  - chunk_id       │
  │  - text           │
  │  - embedding[384] │
  │  - metadata{}     │
  └──────────────────┘
```

### Component: `src/ingestion/embedder.py`

| Responsibility | Detail |
|---|---|
| **Input** | List of `TextChunk` objects |
| **Output** | Embedded vectors stored in ChromaDB (Phase 4) |
| **Model** | `sentence-transformers/all-MiniLM-L6-v2` from HuggingFace |
| **Batch processing** | Embed all chunks in a single batch call for efficiency |
| **Normalization** | L2-normalize vectors (ChromaDB does this by default for cosine similarity) |

### Model Specification

| Property | Value |
|---|---|
| Model name | `all-MiniLM-L6-v2` |
| Source | HuggingFace `sentence-transformers` |
| Embedding dimensions | 384 |
| Max input tokens | 256 |
| Parameters | ~22M |
| Inference | CPU-only (no GPU required) |
| Similarity metric | Cosine similarity |
| Cost | Free / open-source |

### Key Design Decision
> **Same model for ingestion and query.** The PRD mandates using `all-MiniLM-L6-v2` for both chunk embedding (Phase 3) and query embedding (Phase 5). This ensures vectors live in the same semantic space.

---

## 5. Phase 4 — Vector Store

### Purpose
Persist all embedded chunks with their metadata in ChromaDB for fast similarity-based retrieval at query time.

### Architecture

```
  ┌──────────────────┐         ┌──────────────────────────────┐
  │  EmbeddedChunks   │         │          ChromaDB            │
  │  (from Phase 3)   │────────►│                              │
  │                    │  upsert │  Collection: "groww_funds"   │
  └──────────────────┘         │                              │
                               │  Storage per document:       │
                               │  ┌────────────────────────┐  │
                               │  │ ID:        chunk_id     │  │
                               │  │ Embedding: float[384]   │  │
                               │  │ Document:  chunk text    │  │
                               │  │ Metadata:               │  │
                               │  │   source_url: str       │  │
                               │  │   fund_name: str        │  │
                               │  │   fund_category: str    │  │
                               │  │   scrape_timestamp: str │  │
                               │  └────────────────────────┘  │
                               │                              │
                               │  Persistence:                │
                               │   data/chroma_db/            │
                               │                              │
                               │  Distance metric: cosine     │
                               └──────────────────────────────┘
```

### Component: `src/ingestion/embedder.py` (storage logic)

| Responsibility | Detail |
|---|---|
| **Collection name** | `groww_funds` (single collection for all 5 funds) |
| **Persistence path** | `data/chroma_db/` (local filesystem) |
| **Distance function** | Cosine similarity (`cosine`) |
| **Upsert strategy** | Use `chunk_id` as the document ID. Re-running ingestion overwrites stale data. |
| **Metadata stored** | `source_url`, `fund_name`, `fund_category`, `scrape_timestamp` |

### ChromaDB Collection Schema

```python
collection = chroma_client.get_or_create_collection(
    name="groww_funds",
    metadata={"hnsw:space": "cosine"}  # Cosine similarity
)

collection.upsert(
    ids=["large_cap_0", "large_cap_1", ...],        # chunk_id
    embeddings=[[0.012, -0.034, ...], ...],          # float[384]
    documents=["The expense ratio of...", ...],       # chunk text
    metadatas=[{                                      # per-chunk metadata
        "source_url": "https://groww.in/mutual-funds/...",
        "fund_name": "HDFC Large Cap Fund Direct Growth",
        "fund_category": "Large Cap",
        "scrape_timestamp": "2026-09-02T10:00:00+05:30"
    }, ...]
)
```

### Storage Estimates

| Metric | Estimate |
|---|---|
| Total chunks | ~25–75 |
| Embedding size per chunk | 384 × 4 bytes = 1.5 KB |
| Total embedding storage | ~37–112 KB |
| Metadata + text storage | ~50–150 KB |
| **Total ChromaDB size** | **< 1 MB** |

---

## 6. Phase 5 — Retrieval Logic

### Purpose
At runtime, take a user's natural-language question, retrieve the most relevant chunks from ChromaDB, construct a grounded prompt, and generate a factual answer via Mistral LLM — all within the PRD's guardrails.

### Architecture

```
  ┌───────────┐
  │ User Query │
  │ (Streamlit)│
  └─────┬─────┘
        │
        ▼
  ┌───────────────────┐     ┌───────────────────┐
  │  GUARDRAIL LAYER   │     │  PII Patterns:     │
  │                     │◄────│  PAN: [A-Z]{5}\d{4}│
  │  1. PII Filter      │     │  Aadhaar: \d{12}   │
  │  2. Intent Classifier│     │  Email, Phone, OTP │
  │                     │     └───────────────────┘
  └─────┬──────────────┘
        │
        │ [BLOCKED] ──► Return PII/advisory refusal message
        │
        │ [PASSED]
        ▼
  ┌───────────────────┐
  │  Query Embedding   │
  │  all-MiniLM-L6-v2  │
  │  → float[384]      │
  └─────┬─────────────┘
        │
        ▼
  ┌───────────────────┐
  │  ChromaDB Query    │
  │                    │
  │  collection.query( │
  │    query_embedding,│
  │    n_results=3-5   │
  │  )                 │
  │                    │
  │  Returns:          │
  │  - Top-K chunks    │
  │  - Distances       │
  │  - Metadata        │
  └─────┬─────────────┘
        │
        ▼
  ┌───────────────────┐
  │  Relevance Check   │
  │                    │
  │  If max_similarity │
  │  < threshold (0.3) │
  │  → "No relevant    │
  │    info found"     │
  └─────┬─────────────┘
        │ [RELEVANT]
        ▼
  ┌───────────────────┐
  │  Prompt Builder    │
  │                    │
  │  System Prompt:    │
  │  + Facts-only rule │
  │  + ≤3 sentences    │
  │  + Citation rule   │
  │  + No advisory     │
  │  + No returns data │
  │                    │
  │  Context:          │
  │  + Top-K chunk text│
  │  + Source URLs     │
  │                    │
  │  User Question:    │
  │  + Original query  │
  └─────┬─────────────┘
        │
        ▼
  ┌───────────────────┐
  │  Mistral LLM       │
  │  (API call)        │
  │                    │
  │  Model: mistral-   │
  │   small-latest     │
  │                    │
  │  Temperature: 0.1  │
  │  (low creativity,  │
  │   high factuality) │
  └─────┬─────────────┘
        │
        ▼
  ┌───────────────────┐
  │  Response Format   │
  │                    │
  │  Answer (≤3 sent.) │
  │  Source: [URL]     │
  │  Last updated:     │
  │   <scrape_date>    │
  └───────────────────┘
```

### Components

#### `src/retrieval/retriever.py`

| Responsibility | Detail |
|---|---|
| **Input** | User query string |
| **Processing** | Embed query → ChromaDB similarity search → return Top-K results |
| **Output** | `RetrievalResult` with chunks, distances, and metadata |
| **Top-K** | Default K = 3. Configurable up to 5. |
| **Similarity threshold** | Discard results with cosine distance > 0.7 (i.e., similarity < 0.3) |

#### `src/retrieval/prompt_builder.py`

| Responsibility | Detail |
|---|---|
| **Input** | Retrieved chunks + user query |
| **Output** | Fully assembled prompt string for Mistral |
| **System prompt** | Enforces all PRD guardrails (facts-only, ≤3 sentences, citation, no advisory, no returns) |

#### `src/generation/llm_client.py`

| Responsibility | Detail |
|---|---|
| **Input** | Assembled prompt |
| **Output** | LLM-generated answer string |
| **Model** | `mistral-small-latest` (via `mistralai` Python SDK) |
| **Temperature** | 0.1 (factual, deterministic) |
| **Max tokens** | 250 (sufficient for ≤3 sentences + citation) |
| **API key** | Loaded from `.env` via `python-dotenv` |
| **Error handling** | Timeout: 10s. Retry: 2×. Fallback: user-friendly error message. |

### System Prompt Template

```
You are a facts-only FAQ assistant for HDFC mutual funds on Groww.in.

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
{retrieved_chunks}

SOURCE URLS:
{source_urls}

USER QUESTION:
{user_query}
```

### Guardrail Components

#### `src/guardrails/pii_filter.py`

| Pattern | Regex | Action |
|---|---|---|
| PAN | `[A-Z]{5}\d{4}[A-Z]` | Block + warn |
| Aadhaar | `\d{4}\s?\d{4}\s?\d{4}` | Block + warn |
| Email | `[\w.-]+@[\w.-]+\.\w+` | Block + warn |
| Phone | `(\+91[\-\s]?)?[6-9]\d{9}` | Block + warn |
| OTP | `\b\d{4,6}\b` (in OTP context) | Block + warn |

#### `src/guardrails/intent_classifier.py`

| Intent | Detection Strategy | Action |
|---|---|---|
| Advisory / Buy-Sell | Keyword match: `should I`, `buy`, `sell`, `recommend`, `better than`, `which fund` | Polite refusal + educational link |
| Performance query | Keyword match: `returns`, `performance`, `CAGR`, `NAV history` | Refuse + link to factsheet |
| Factual | Default (passes through) | Proceed to retrieval |

---

## 7. Phase 6 — Retrieval Testing

### Purpose
Validate the entire RAG pipeline against the PRD's success metrics (PRD §11) and edge cases (PRD §9).

### Test Architecture

```
  ┌────────────────────────────────────────────────────────────────┐
  │                     TEST SUITE                                 │
  │                                                                │
  │  ┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐ │
  │  │ test_retrieval.py │  │test_guard    │  │test_edge_cases.py│ │
  │  │                   │  │rails.py      │  │                  │ │
  │  │ • Accuracy tests  │  │ • PII block  │  │ • Out-of-scope   │ │
  │  │ • Citation tests  │  │ • Advisory   │  │ • Ambiguous      │ │
  │  │ • Relevance tests │  │   refusal    │  │ • Gibberish      │ │
  │  │ • Latency tests   │  │ • Perf query │  │ • API failure    │ │
  │  │ • Brevity tests   │  │   refusal    │  │ • No-match       │ │
  │  └──────────────────┘  └──────────────┘  └──────────────────┘ │
  └────────────────────────────────────────────────────────────────┘
```

### Test Plan

#### 7.1 `tests/test_retrieval.py` — Retrieval Accuracy & Quality

| Test ID | Test Case | Input | Expected Outcome | PRD Metric |
|---|---|---|---|---|
| R-01 | Expense ratio query | "What is the expense ratio of HDFC Large Cap Fund?" | Correct expense ratio value from Large Cap page | Factual Accuracy ≥ 90% |
| R-02 | Exit load query | "What is the exit load for HDFC Small Cap Fund?" | Correct exit load from Small Cap page | Factual Accuracy ≥ 90% |
| R-03 | Lock-in period | "What is the ELSS lock-in period?" | "3 years" from ELSS page | Factual Accuracy ≥ 90% |
| R-04 | Minimum SIP | "Minimum SIP for HDFC Flexi Cap?" | Correct min SIP from Flexi Cap page | Factual Accuracy ≥ 90% |
| R-05 | Riskometer | "Riskometer of HDFC Balanced Advantage?" | Correct risk category | Factual Accuracy ≥ 90% |
| R-06 | Benchmark | "What benchmark does HDFC Large Cap track?" | Correct benchmark index | Factual Accuracy ≥ 90% |
| R-07 | Citation present | Any factual query | Response contains a valid `groww.in/mutual-funds/...` URL | Citation Accuracy = 100% |
| R-08 | Citation correct | "Exit load of HDFC Small Cap?" | Citation points to Small Cap page, not another fund | Citation Accuracy = 100% |
| R-09 | Answer brevity | Any factual query | Response ≤ 3 sentences | Brevity ≤ 3 sentences |
| R-10 | Response latency | Any factual query | End-to-end < 5 seconds | Latency < 5s |

#### 7.2 `tests/test_guardrails.py` — PII & Intent Filtering

| Test ID | Test Case | Input | Expected Outcome | PRD Metric |
|---|---|---|---|---|
| G-01 | PAN detection | "My PAN is ABCDE1234F" | Blocked before LLM. Warning displayed. | PII Rejection = 100% |
| G-02 | Aadhaar detection | "Aadhaar: 1234 5678 9012" | Blocked before LLM. | PII Rejection = 100% |
| G-03 | Email detection | "Send to user@email.com" | Blocked before LLM. | PII Rejection = 100% |
| G-04 | Phone detection | "+91 9876543210" | Blocked before LLM. | PII Rejection = 100% |
| G-05 | Advisory refusal | "Should I buy HDFC Small Cap?" | Polite refusal + educational link | Refusal Rate ≥ 95% |
| G-06 | Comparison refusal | "Is HDFC Flexi Cap better than SBI Flexi Cap?" | Polite refusal | Refusal Rate ≥ 95% |
| G-07 | Performance refusal | "What are the 5-year returns?" | Refuse + link to factsheet | Refusal Rate ≥ 95% |
| G-08 | Transactional refusal | "Sell my ELSS units" | Polite refusal | Refusal Rate ≥ 95% |

#### 7.3 `tests/test_edge_cases.py` — Boundary & Error Conditions

| Test ID | Test Case | Input | Expected Outcome |
|---|---|---|---|
| E-01 | Out-of-scope fund | "Tell me about Axis Bluechip" | Lists the 5 supported funds |
| E-02 | Ambiguous query | "expense ratio?" | Asks which of the 5 funds |
| E-03 | Gibberish input | "asdfghjkl" | "I didn't understand..." + example questions |
| E-04 | Empty input | "" | Prompt for a question + examples |
| E-05 | No relevant chunks | "What is the weather today?" | "I couldn't find relevant information..." |
| E-06 | Multi-fund factual | "Exit loads of all 5 funds?" | Factual answer for each fund, no comparison |
| E-07 | LLM timeout | (Simulated API timeout) | User-friendly error message |
| E-08 | Chunk boundary fact | Query about a fact that might span chunk boundaries | Correct answer (validates overlap strategy) |

### Test Execution

```bash
# Run all tests
pytest tests/ -v

# Run specific phase tests
pytest tests/test_retrieval.py -v      # Phase 6a: Retrieval accuracy
pytest tests/test_guardrails.py -v     # Phase 6b: Guardrail validation
pytest tests/test_edge_cases.py -v     # Phase 6c: Edge cases
```

### Success Criteria (from PRD §11)

| Metric | Target | Pass/Fail |
|---|---|---|
| Factual Accuracy | ≥ 90% (18/20 curated questions) | ☐ |
| Citation Accuracy | 100% | ☐ |
| Advisory Refusal | ≥ 95% (9.5/10 advisory questions) | ☐ |
| PII Rejection | 100% | ☐ |
| Response Latency | < 5 seconds | ☐ |
| Answer Brevity | ≤ 3 sentences | ☐ |

---

## 8. Cross-Cutting Concerns

### 8.1 Configuration Management

```
.env (gitignored)
├── MISTRAL_API_KEY=sk-...
├── CHROMA_PERSIST_PATH=data/chroma_db/
├── EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
├── LLM_MODEL=mistral-small-latest
├── LLM_TEMPERATURE=0.1
├── LLM_MAX_TOKENS=250
├── RETRIEVAL_TOP_K=3
└── SIMILARITY_THRESHOLD=0.3
```

### 8.2 Logging

| Layer | What to Log |
|---|---|
| Scraper | URL, status code, chars extracted, errors |
| Chunker | Document → chunk count, avg chunk size |
| Embedder | Batch size, embedding time, ChromaDB upsert count |
| Retriever | Query, top-K distances, selected chunks |
| Guardrails | Blocked queries (PII type / intent type) — **no PII values logged** |
| LLM Client | Prompt token count, response token count, latency |

### 8.3 Error Handling Strategy

| Error Type | Handling |
|---|---|
| Scrape failure (HTTP 4xx/5xx) | Retry 3× → skip URL → log warning |
| ChromaDB connection error | Fail fast with clear error message |
| Mistral API error (rate limit / timeout) | Retry 2× → return user-friendly fallback |
| Embedding model load failure | Fail fast → check `sentence-transformers` install |

---

## 9. File-to-Phase Mapping

```
anti build hrs/
│
├── data/                        ──── ALL PIPELINE DATA (separated by stage)
│   ├── raw/                     ──── Phase 1 output (scraped HTML/text per fund)
│   ├── chunks/                  ──── Phase 2 output (chunked JSON documents)
│   ├── embeddings/              ──── Phase 3 output (cached embeddings, optional)
│   └── chroma_db/               ──── Phase 4 store (ChromaDB persistent storage)
│
├── src/                         ──── ALL CODE FILES
│   ├── __init__.py
│   ├── app.py                   ──── Streamlit entry point (UI)
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── scraper.py           ──── Phase 1 (Data Loading)
│   │   ├── chunker.py           ──── Phase 2 (Chunking)
│   │   └── embedder.py          ──── Phase 3 (Embedding) + Phase 4 (Vector Store)
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── retriever.py         ──── Phase 5 (Retrieval Logic — query + search)
│   │   └── prompt_builder.py    ──── Phase 5 (Retrieval Logic — prompt assembly)
│   ├── generation/
│   │   ├── __init__.py
│   │   └── llm_client.py        ──── Phase 5 (Retrieval Logic — LLM call)
│   └── guardrails/
│       ├── __init__.py
│       ├── pii_filter.py        ──── Phase 5 (Retrieval Logic — PII pre-filter)
│       └── intent_classifier.py ──── Phase 5 (Retrieval Logic — intent pre-filter)
│
├── tests/                       ──── ALL TEST FILES
│   ├── __init__.py
│   ├── test_retrieval.py        ──── Phase 6 (Retrieval accuracy & quality)
│   ├── test_guardrails.py       ──── Phase 6 (PII & intent filter validation)
│   └── test_edge_cases.py       ──── Phase 6 (Boundary & error conditions)
│
├── docs/                        ──── DOCUMENTATION
│   ├── problemstatement.txt     ──── Original problem statement
│   ├── PRD.md                   ──── Product Requirements Document
│   └── architecture.md          ──── THIS DOCUMENT
│
├── .env.example                 ──── Config template (copy to .env)
├── .gitignore                   ──── Excludes .env, chroma_db/, __pycache__/
├── requirements.txt             ──── Python dependencies
└── README.md                    ──── Project documentation
```

---

## 10. Dependency Graph

```
Phase 1 (Data Loading)
    │
    ▼
Phase 2 (Chunking)        ← Depends on Phase 1 output (ScrapedDocument)
    │
    ▼
Phase 3 (Embedding)        ← Depends on Phase 2 output (TextChunk)
    │
    ▼
Phase 4 (Vector Store)     ← Depends on Phase 3 output (embedded vectors)
    │
    ▼
Phase 5 (Retrieval Logic)  ← Depends on Phase 4 (populated ChromaDB)
    │                        ← Also depends on Mistral API key (.env)
    ▼
Phase 6 (Retrieval Testing) ← Depends on all prior phases being functional
```

> **Build order is strictly sequential.** Each phase must be completed and validated before the next begins.

---

*End of Architecture Document*
