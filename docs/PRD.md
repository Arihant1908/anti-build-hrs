# Product Requirements Document (PRD)
## Groww × HDFC Mutual Fund — RAG FAQ Chatbot Prototype

| Field | Detail |
|---|---|
| **Author** | PM (Prototype Build) |
| **Created** | 2026-09-02 |
| **Status** | Draft |
| **Type** | Prototype / Hobby Project |

---

## 1. Problem Statement

Investors browsing HDFC mutual fund pages on [Groww.in](https://groww.in/) frequently have factual questions — expense ratios, exit loads, lock-in periods, minimum SIP amounts, riskometer categories, and more. Today they must manually scan the page or search external sources, often landing on unreliable third-party blogs.

**We are building a RAG-based FAQ chatbot prototype** that instantly answers factual queries about five specific HDFC mutual fund schemes listed on Groww, grounded entirely in publicly available page data, with citations.

> **IMPORTANT:** This is a **prototype / hobby project** to test and validate a RAG pipeline end-to-end — not a production-grade product.

---

## 2. Goals & Non-Goals

### Goals
| # | Goal |
|---|---|
| G1 | Answer factual mutual fund queries (expense ratio, SIP minimum, exit load, lock-in, benchmark, etc.) accurately using only the scraped Groww page data. |
| G2 | Provide a clear **citation link** back to the source Groww page in every answer. |
| G3 | Gracefully **refuse opinionated / advisory questions** ("Should I buy?", "Is this better than X?") with a polite facts-only message and a relevant educational link. |
| G4 | Validate the full RAG pipeline: Ingest → Chunk → Embed → Store → Retrieve → Generate. |
| G5 | Deliver a working **Streamlit UI** that mirrors the Groww brand color palette. |

### Non-Goals
| # | Non-Goal |
|---|---|
| NG1 | Production deployment, scalability, or multi-tenant support. |
| NG2 | Handling PII (PAN, Aadhaar, phone, email, OTP, account numbers). |
| NG3 | Computing, comparing, or displaying fund performance / returns. |
| NG4 | Ingesting data from any source beyond the 5 scoped URLs. |
| NG5 | Supporting voice, multilingual, or mobile-native interfaces. |

---

## 3. Scoped Data Corpus (5 URLs — No Exceptions)

Only data from the following pages will be ingested. **No third-party blogs, no app back-end screenshots, no additional URLs.**

| # | Fund Category | Fund Name | Groww URL |
|---|---|---|---|
| 1 | Large Cap | HDFC Large Cap Fund Direct Growth | [Link](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth) |
| 2 | Flexi Cap | HDFC Flexi Cap Fund Direct Growth | [Link](https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth) |
| 3 | ELSS | HDFC ELSS Tax Saver Fund Direct Plan Growth | [Link](https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth) |
| 4 | Small Cap | HDFC Small Cap Fund Direct Growth | [Link](https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth) |
| 5 | Hybrid | HDFC Balanced Advantage Fund Direct Growth | [Link](https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth) |

> **NOTE:** Fund #2 uses the legacy slug `hdfc-equity-fund-direct-growth` from the fund's previous name.

---

## 4. Key Constraints & Guardrails

| Constraint | Enforcement |
|---|---|
| **Public sources only** | Scrape only the 5 scoped Groww URLs. No screenshots of app back-end; no third-party content. |
| **No PII** | The chatbot must **never accept or store** PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers. Input sanitization required. |
| **No performance claims** | Never compute or compare returns. If asked, respond with a link to the official fund factsheet. |
| **Clarity & transparency** | Answers ≤ 3 sentences. Every answer must include: `"Last updated from sources: <date>"`. |
| **Citation required** | Every answer includes one clear citation link to the source Groww page. |

---

## 5. System Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION (Offline / One-time)              │
│                                                                     │
│  5 Groww URLs ──► Web Scrape ──► Chunking ──► Embedding ──► ChromaDB│
│                  (BS4/Playwright) (RecursiveChar)  (MiniLM-L6-v2)  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    QUERY PIPELINE (Runtime)                         │
│                                                                     │
│  User Question ──► PII Check ──► Embed Query ──► ChromaDB Search   │
│                         │              │               │            │
│                    [Block if PII]      │          Top-K Chunks      │
│                                        │               │            │
│                                        └───► Prompt Builder         │
│                                                    │                │
│                                              Mistral LLM            │
│                                                    │                │
│                                           Streamlit UI ──► User     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Technical Stack & Components

### 6.1 Data Ingestion Pipeline

| Step | Technology | Details |
|---|---|---|
| **Web Scraping** | `requests` + `BeautifulSoup` / Playwright | Scrape public-facing content from the 5 Groww URLs. Handle JS-rendered content if needed. |
| **Chunking** | Custom splitter / LangChain `RecursiveCharacterTextSplitter` | Split scraped text into meaningful chunks (recommended: 300–500 tokens per chunk with ~50 token overlap). |
| **Embedding** | [`sentence-transformers/all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | Free, lightweight, 384-dimensional embeddings. Runs locally on CPU. |
| **Vector Store** | [ChromaDB](https://www.trychroma.com/) | Local, file-based vector database. No server setup needed. |

### 6.2 Data Retrieval & Answer Generation Pipeline

| Step | Technology | Details |
|---|---|---|
| **Query Embedding** | `sentence-transformers/all-MiniLM-L6-v2` | Same model as ingestion to ensure embedding space consistency. |
| **Retrieval** | ChromaDB similarity search | Top-K nearest chunks (K = 3–5 recommended). |
| **Prompt Construction** | Custom prompt template | System prompt enforces: facts-only, ≤3 sentences, citation link, PII rejection, no advisory answers. |
| **LLM** | **Mistral** (via API key) | Lightweight, fast inference. Use `mistral-small` or `mistral-medium` tier. |
| **Answer Generation** | Mistral API | Grounded answer with citation. |

### 6.3 User Interface

| Aspect | Choice |
|---|---|
| **Framework** | Streamlit |
| **Color Palette** | Groww brand colors — Primary: `#00D09C` (green), Background: `#1B1F3B` (dark navy), Text: `#FFFFFF` |
| **Welcome Screen** | Welcome line + 3 example questions + disclaimer: *"Facts-only. No investment advice."* |

---

## 7. User Experience & Interaction Flow

### 7.1 Happy Path (Factual Question)

```
User opens chatbot
    └──► Sees: Welcome message + 3 sample questions + disclaimer
User asks: "What is the expense ratio of HDFC Small Cap Fund?"
    └──► RAG: Embed query → Search ChromaDB → Get top chunks
        └──► Mistral: Generate answer from context
            └──► UI displays: "The expense ratio of HDFC Small Cap Fund
                 Direct Growth is X%. Source: [groww.in/...].
                 Last updated from sources: 2026-09-02"
```

### 7.2 Refusal Path (Advisory / Opinionated Question)

```
User asks: "Should I invest in HDFC ELSS fund?"
    └──► System classifies as opinionated/advisory
        └──► UI displays: "I can only answer factual questions about these
             funds. For investment guidance, consider visiting Groww's
             learning centre. Here are some questions I can help with: ..."
```

### 7.3 PII Detection Path

```
User inputs: "My PAN is ABCDE1234F, check my..."
    └──► PII filter catches PAN pattern BEFORE reaching LLM
        └──► UI displays: "⚠️ I don't accept or store personal information
             (PAN, Aadhaar, phone, email, etc.). Please ask a factual
             question about the mutual funds I cover."
```

---

## 8. Sample Questions the Bot Should Handle

### ✅ Answerable (Factual)

| # | Sample Question | Expected Source |
|---|---|---|
| 1 | "What is the expense ratio of HDFC Large Cap Fund?" | HDFC Large Cap page |
| 2 | "What is the ELSS lock-in period?" | HDFC ELSS page |
| 3 | "What is the minimum SIP amount for HDFC Flexi Cap?" | HDFC Flexi Cap page |
| 4 | "What is the exit load for HDFC Small Cap Fund?" | HDFC Small Cap page |
| 5 | "What is the riskometer category of HDFC Balanced Advantage Fund?" | HDFC Balanced Advantage page |
| 6 | "What benchmark does HDFC Large Cap Fund track?" | HDFC Large Cap page |
| 7 | "How to download capital-gains statement?" | Any relevant page |

### 🚫 Should Be Refused

| # | Sample Question | Reason |
|---|---|---|
| 1 | "Should I buy HDFC Small Cap?" | Investment advice |
| 2 | "Is HDFC Flexi Cap better than SBI Flexi Cap?" | Comparison / opinion |
| 3 | "What are the 5-year returns?" | Performance claim |
| 4 | "Sell my ELSS units" | Transactional / advisory |

---

## 9. Edge Cases & Error Handling

| Edge Case | Expected Behavior |
|---|---|
| **Out-of-scope fund** (e.g., "Tell me about Axis Bluechip") | "I only have information on 5 HDFC funds listed on Groww. [list them]" |
| **PII in input** | Block immediately. Do not pass to LLM. Show warning. |
| **Ambiguous query** (e.g., "expense ratio?") | Ask clarifying question: "Which fund are you asking about?" and list the 5 options. |
| **Gibberish / empty input** | "I didn't quite understand that. Here are some example questions you can ask: ..." |
| **LLM API failure / timeout** | "Sorry, I'm having trouble generating an answer right now. Please try again in a moment." |
| **No relevant chunks retrieved** (low similarity score) | "I couldn't find relevant information for your question in my current data. Try rephrasing, or check the fund pages directly: [links]." |
| **Multi-fund question** ("Compare exit loads of all 5 funds") | Answer factually for each fund if data exists. Do NOT compare performance. |

---

## 10. Competitive Landscape (Lightweight Analysis)

| Solution | Strengths | Weaknesses vs. Our Prototype |
|---|---|---|
| **Groww's in-app search** | Native, trusted | No conversational interface; keyword-based |
| **Generic ChatGPT / Gemini** | Broad knowledge | May hallucinate fund data; no guaranteed citations; uses training data not live page data |
| **Mutual-fund advisory chatbots (e.g., Scripbox, Kuvera)** | Full advisory stack | Opinionated; not facts-only; scope too broad |
| **Our RAG Prototype** | Grounded in real page data; citations; facts-only guardrails | Limited to 5 funds; prototype-grade only |

---

## 11. Success Metrics (Prototype-Grade)

| Metric | Target | How to Measure |
|---|---|---|
| **Factual Accuracy** | ≥ 90% of answerable questions return correct data | Manual test with 20 curated questions |
| **Citation Accuracy** | 100% of answers include the correct source link | Manual verification |
| **Refusal Rate (advisory Qs)** | ≥ 95% of opinionated questions are correctly refused | Test with 10 advisory questions |
| **PII Rejection** | 100% of PII inputs blocked before reaching LLM | Test with PAN, Aadhaar, email, phone patterns |
| **Response Latency** | < 5 seconds end-to-end | Stopwatch / Streamlit profiling |
| **Answer Brevity** | ≤ 3 sentences per answer | Automated sentence count check |

---

## 12. Project Structure (Proposed)

```
anti build hrs/
├── docs/
│   ├── problemstatement.txt
│   └── PRD.md                    ← This document
├── src/
│   ├── ingestion/
│   │   ├── scraper.py            # Web scraper for 5 Groww URLs
│   │   ├── chunker.py            # Text chunking logic
│   │   └── embedder.py           # Embedding + ChromaDB storage
│   ├── retrieval/
│   │   ├── retriever.py          # Query embedding + ChromaDB search
│   │   └── prompt_builder.py     # System prompt + context assembly
│   ├── generation/
│   │   └── llm_client.py         # Mistral API integration
│   ├── guardrails/
│   │   ├── pii_filter.py         # PII detection & blocking
│   │   └── intent_classifier.py  # Advisory vs factual classification
│   └── app.py                    # Streamlit entry point
├── data/
│   └── chroma_db/                # ChromaDB persistent storage
├── tests/
│   ├── test_retrieval.py
│   ├── test_guardrails.py
│   └── test_edge_cases.py
├── .env                          # MISTRAL_API_KEY (gitignored)
├── requirements.txt
└── README.md
```

---

## 13. Dependencies & Requirements

```
streamlit
chromadb
sentence-transformers
mistralai
requests
beautifulsoup4
python-dotenv
```

> **WARNING:** The **Mistral API key** must be stored in a `.env` file and **never committed to version control**. Add `.env` to `.gitignore`.

---

## 14. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Groww pages are JS-rendered; `requests` may not get full content | Missing data → inaccurate answers | Use Playwright/Selenium as fallback scraper |
| Mistral API rate limits or downtime | Chatbot becomes unresponsive | Add retry logic + user-friendly error messages |
| Embedding model quality on financial text | Poor retrieval accuracy | Test with sample queries; consider fine-tuned embeddings if accuracy is low |
| Stale data (fund details change) | Outdated answers | Display "Last updated" timestamp; re-scrape periodically |
| Prompt injection via user input | LLM may bypass guardrails | Input sanitization + system prompt hardening + PII regex pre-filter |

---

## 15. Milestone Plan

| Phase | Deliverable | Estimated Effort |
|---|---|---|
| **Phase 1 — Ingestion** | Scrape 5 URLs → Chunk → Embed → Store in ChromaDB | 3–4 hours |
| **Phase 2 — Retrieval + Generation** | Query pipeline: embed question → retrieve → Mistral prompt → answer | 3–4 hours |
| **Phase 3 — Guardrails** | PII filter, advisory question refusal, out-of-scope handling | 2–3 hours |
| **Phase 4 — Streamlit UI** | Groww-themed chat UI with welcome screen + example Qs | 2–3 hours |
| **Phase 5 — Testing & Polish** | Edge case testing, accuracy validation, README | 2–3 hours |
| **Total** | **Working Prototype** | **~12–17 hours** |

---

## 16. Open Questions

> **These need answers before or during implementation:**

1. **Scraping strategy**: Do the Groww pages require JavaScript rendering, or is static HTML sufficient? (Determines `requests+BS4` vs `Playwright`.)
2. **Mistral model tier**: Use `mistral-small-latest` (cheaper, faster) or `mistral-medium-latest` (better quality)? Budget considerations?
3. **Chunk size tuning**: Start with 400 tokens / 50 overlap — acceptable, or do you have a preference?
4. **Refresh cadence**: How often should we re-scrape the 5 pages to keep data current? (Daily? Weekly? Manual trigger?)
5. **Hosting**: Is this purely local, or do you want a Streamlit Cloud / Hugging Face Spaces deployment?

---

*End of PRD*
