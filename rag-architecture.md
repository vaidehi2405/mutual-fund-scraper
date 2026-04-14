# RAG Architecture for Milestone 1 (Mutual Fund Facts-Only FAQ)

This architecture is designed specifically for the requirements in `problem statement.md`: small curated corpus, facts-only answers, mandatory citation per answer, concise responses, and safe refusal for advice/opinion queries.

---

## 1) Goal and Non-Goals

### Goal
Build a Retrieval-Augmented Generation (RAG) assistant that answers only factual questions about mutual fund schemes from official public sources (AMC/SEBI/AMFI), with exactly one clear source link in every answer.

### Non-Goals
- No investment advice, portfolio allocation, buy/sell recommendations.
- No return comparison/computation or performance ranking.
- No user onboarding or account-linked functionality.
- No storage of sensitive personal information.

---

## 2) Product Scope (Dataset Boundary)

Selected product context: `Groww`.  
All milestones will use `Groww` as the product context.

For Milestone 1 retrieval corpus:
- Choose **1 AMC**.
- Choose **3-5 schemes** under that AMC:
  - one large-cap,
  - one flexi-cap,
  - one ELSS,
  - plus optional 1-2 additional schemes.
- Collect **15-25 official URLs** only from AMC/SEBI/AMFI:
  - factsheets,
  - KIM/SID pages or PDFs,
  - scheme FAQ pages,
  - fee/charges pages,
  - riskometer/benchmark notes,
  - statement/capital-gains/tax document guides.

### 2.1 URL List to Scrape

#### Fund: ICICI Prudential Large Cap Fund
- SID: https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doGetFundDetails=yes
- Factsheet: https://www.icicipruamc.com/blob/knowledgecenter/factsheet
- KIM: https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doGetFundDetails=yes
- Product Page: https://groww.in/mutual-funds/icici-prudential-large-cap-fund

#### Fund: ICICI Prudential Flexicap Fund
- SID: https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doGetFundDetails=yes
- Factsheet: https://www.icicipruamc.com/blob/knowledgecenter/factsheet
- KIM: https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doGetFundDetails=yes
- Product Page: https://groww.in/mutual-funds/icici-prudential-flexicap-fund

#### Fund: ICICI Prudential Midcap Fund
- SID: https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doGetFundDetails=yes
- Factsheet: https://www.icicipruamc.com/blob/knowledgecenter/factsheet
- KIM: http://sebi.gov.in/sebiweb/other/OtherAction.do?doGetFundDetails=yes
- Product Page: https://groww.in/mutual-funds/icici-prudential-midcap-fund

#### Fund: ICICI Prudential Smallcap Fund
- SID: https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doGetFundDetails=yes
- Factsheet: https://www.icicipruamc.com/blob/knowledgecenter/factsheet
- KIM: https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doGetFundDetails=yes
- Product Page: https://groww.in/mutual-funds/icici-prudential-smallcap-fund

#### Fund: ICICI Prudential ELSS Tax Saver Fund
- SID: https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doGetFundDetails=yes
- Factsheet: https://www.icicipruamc.com/blob/knowledgecenter/factsheet
- KIM: https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doGetFundDetails=yes
- Product Page: https://groww.in/mutual-funds/icici-prudential-elss-tax-saver-fund

#### Additional Official Source Links
- SEBI Fund Details: https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doGetFundDetails=yes
- ICICI Prudential AMC FAQs: https://www.icicipruamc.com/help-center/faqs

### 2.2 Scraping Schedule
- Run the source scraping pipeline **every day at 9:15 AM** using **GitHub Actions** scheduling.
- Update `last_checked_at` on every successful scrape.
- If scrape fails, retain last successful indexed version and log failure reason.

---

## 3) High-Level System Architecture

```text
User Query
   |
   v
[Input Guardrail Layer]
  - PII detector/redactor
  - Advice/opinion intent classifier
  - Allowed-topic checker (MF factual scope)
   |
   +-- if disallowed --> [Safe Refusal Response + educational official link]
   |
   v
[Query Understanding Layer]
  - Query normalization (scheme/entity extraction)
  - Intent typing (expense ratio / exit load / SIP / lock-in / riskometer / benchmark / statement process)
   |
   v
[Retriever Layer]
  - Hybrid retrieval (keyword + vector)
  - Metadata filters (AMC, scheme, doc type, recency)
  - Top-k candidate chunks
   |
   v
[Reranker / Evidence Selector]
  - Select best evidence chunk
  - Ensure source is official and valid
   |
   v
[Answer Generator]
  - Facts-only constrained prompt
  - <=3 sentence answer
  - Exactly one citation link
  - "Last updated from sources: <date>"
   |
   v
[Response Validator]
  - Checks for advice language
  - Checks citation presence/format
  - Checks sentence limit
  - Checks source-domain allowlist
   |
   v
Final Response to UI
```

---

## 4) Core Components in Detail

## 4.1 Source Ingestion Pipeline

### Input
- Manual source list file (`sources.csv` or `sources.md`) with:
  - `url`
  - `source_type` (factsheet, KIM, SID, FAQ, guide, regulator page)
  - `amc`
  - `scheme`
  - `official_domain_flag`
  - `last_checked_at`

### Fetching
- Crawl/fetch each URL (HTML/PDF support).
- Convert documents to normalized plain text.
- Keep section headings for context.
- Run scheduled scrape daily at **9:15 AM** via **GitHub Actions** to refresh source content.

### Sanitization
- Strip navigation/footer boilerplate.
- Preserve tables/structured values where possible.
- Deduplicate repeated blocks.

### Chunking Strategy
- Chunk size: ~500-900 characters.
- Overlap: ~80-120 characters.
- Keep heading-context prefixed in each chunk.
- Preserve chunk-level URL and section anchor.

### Metadata per Chunk
- `chunk_id`
- `url`
- `domain`
- `amc`
- `scheme`
- `doc_type`
- `section_title`
- `published_or_effective_date` (if available)
- `ingested_at`

---

## 4.2 Indexing Layer

Use dual index for reliability in small financial corpora:

1. **Vector Index**
   - Embeddings generated for each chunk.
   - Good for semantic matches ("capital gains statement" vs "tax statement download").

2. **Keyword/BM25 Index**
   - Strong for exact terms and numbers:
     - "expense ratio",
     - "exit load",
     - scheme names,
     - "minimum SIP",
     - "lock-in period".

3. **Hybrid Retriever**
   - Weighted merge of vector + BM25 scores.
   - Prefer chunks where scheme/entity metadata matches extracted entities.

---

## 4.3 Query Processing and Routing

### Step A: Normalize Query
- Lowercase normalization.
- Expand common variants:
  - "ER" -> "expense ratio"
  - "cg statement" -> "capital gains statement"
  - "ELSS lock in" -> "ELSS lock-in period".

### Step B: Intent Classification
Supported intents:
- Expense ratio
- Exit load
- Minimum SIP/lumpsum
- ELSS lock-in
- Riskometer
- Benchmark
- Statement/capital-gains/tax-download process
- Source request ("show source")

Out-of-scope intents:
- Buy/sell recommendation
- Portfolio optimization
- Return prediction
- "Best fund" ranking
- Personal suitability advice

### Step C: Guardrail Decision
- If out-of-scope or advice-seeking -> safe refusal template.
- If factual and in-scope -> retrieval path.

---

## 4.4 Retrieval and Evidence Selection

### Candidate Retrieval
- Top-k from hybrid retrieval (e.g., k=8).
- Apply metadata filters where entities are known:
  - `amc == selected_amc`
  - `scheme == extracted_scheme` (if detected).

### Reranking
- Rerank by:
  1. intent-term exactness,
  2. scheme match quality,
  3. recency/effective date (if available),
  4. official source confidence.

### Evidence Choice Rule
- Select one primary evidence chunk for final citation.
- If multiple chunks conflict, either:
  - pick newest official source, or
  - answer with "I could not verify from current sources" + official link.

---

## 4.5 Generation Layer (Constrained Answering)

### Prompt Contract
System prompt constraints:
- Answer factual mutual fund query only.
- No advice/suitability language.
- Keep answer <=3 sentences.
- Include exactly one citation URL from provided evidence.
- Append `Last updated from sources: <date>`.
- If insufficient evidence, say so clearly and provide the best official link.

### Output Template
```text
<Answer in max 3 sentences.>
Source: <one official URL>
Last updated from sources: <YYYY-MM-DD>
```

---

## 4.6 Safety, Compliance, and Refusal Layer

### Advice Refusal
For queries like "Should I buy/sell this fund?":
- Respond politely with facts-only boundary.
- Provide one educational official link (AMC/SEBI/AMFI).
- Do not provide implied recommendations.

### PII Handling
- Input scanner rejects or redacts:
  - PAN, Aadhaar, account numbers, OTPs, email, phone.
- Do not log raw sensitive strings.
- Store only sanitized query logs.

### Claims Control
- Never calculate or compare returns.
- For performance-related asks:
  - redirect to official factsheet link.

---

## 4.7 Response Validation Layer (Post-Generation Checks)

Before returning response:
1. Has `Source:` with exactly one URL?
2. Is URL in allowlisted official domains?
3. Is response <=3 sentences (excluding source/date lines)?
4. Any prohibited advice phrases present?
5. Does response include `Last updated from sources:`?

If any check fails -> auto-regenerate once with stricter prompt; if still failing -> return safe fallback response.

---

## 5) Data Model

Suggested files/tables:

- `sources.csv`
  - `source_id,url,domain,doc_type,amc,scheme,last_checked_at,status`

- `chunks.parquet` (or JSONL)
  - `chunk_id,source_id,text,section_title,amc,scheme,doc_type,effective_date,embedding_vector`

- `query_logs.jsonl` (sanitized)
  - `timestamp,query_sanitized,intent,decision(answer/refuse),source_url,response_status,latency_ms`

- `sample_qa.md`
  - 5-10 representative queries with final answers and links.

---

## 6) UI Architecture (Tiny UI Requirement)

Single-page minimal interface:
- Welcome line:
  - "Ask factual mutual fund questions from official sources."
- 3 example questions:
  - "What is the expense ratio of <scheme>?"
  - "What is the ELSS lock-in period for <scheme>?"
  - "How do I download capital gains statement?"
- Fixed note:
  - "Facts-only. No investment advice."
- Chat area:
  - user query,
  - assistant answer,
  - source line,
  - last-updated line.

---

## 7) Recommended Folder Structure

```text
LIP-2/
  problem statement.md
  rag-architecture.md
  README.md
  data/
    sources.csv
    raw/
    processed/
    chunks.jsonl
  index/
    vector_index/
    bm25_index/
  app/
    ui.py (or app.js)
    rag_pipeline.py
    prompts.py
    guardrails.py
  eval/
    sample_qa.md
    checks.md
```

---

## 8) Evaluation and Acceptance Criteria

### Functional Checks
- Factual questions answered with relevant fact and one official citation.
- Advice/opinion questions politely refused.
- Answer length limit respected.
- "Last updated from sources:" always present.

### Quality Checks
- Citation URL resolves and matches answer context.
- Scheme-specific answers do not leak to wrong scheme.
- Statement-download answers point to official process pages.

### Milestone Completion Checks
- Corpus size between 15 and 25 official URLs.
- Scope clearly documented (AMC + 3-5 schemes).
- Sample Q&A includes 5-10 examples with links.

---

## 9) Implementation Phases

### Phase 1: Corpus Setup
- Finalize AMC and scheme list.
- Curate source list and verify official domains.

### Phase 2: Ingestion + Indexing
- Parse HTML/PDF.
- Chunk and embed.
- Build BM25 and vector indexes.
- Configure **GitHub Actions** scheduled workflow to run every day at **9:15 AM**.

### Phase 3: QA Pipeline
- Implement intent classifier + guardrails.
- Implement hybrid retrieval + reranker.
- Implement constrained answer generation.

### Phase 4: UI + Logging
- Build tiny UI with required disclaimer and examples.
- Add sanitized query logs and basic telemetry.

### Phase 5: Evaluation + Deliverables
- Prepare sample Q&A file.
- Finalize README, sources list, and demo.

---

## 10) Known Limits and Risk Mitigations

### Limits
- Official pages may update without stable change logs.
- PDF extraction quality can vary for tabular fee data.
- Small corpus may miss rare wording variations.

### Mitigations
- Add `last_checked_at` and fixed daily refresh job at **9:15 AM** using **GitHub Actions**.
- Keep chunking heading-aware for precise facts.
- Expand query normalization dictionary over time.
- Use fallback "unable to verify from current sources" when confidence is low.

---

## 11) Suggested Disclaimer Snippet (UI)

"This assistant provides facts from official AMC/SEBI/AMFI sources only. It does not provide investment advice, recommendations, or return comparisons. Please verify details from the cited source link."

