# CLAUSE-LEVEL RETRIEVAL AUDIT REPORT
**Project Codebase Audit: LexiGuard AI & LEDGAR Classifier**  
**Date of Audit**: October 19, 2026  
**Scope**: Code-grounded inspection of `lexiguard-ai` and `LEDGAR_DeBERTa_Project`. (LEDGAR only; CUAD and legacy NLP excluded).

---

## Executive Summary

This audit establishes the concrete, implementation-grounded baseline for the proposed research direction: **Failure-Aware Clause-Level Retrieval with Targeted Evidence Recovery**.

The audit confirms:
1. **There is currently NO clause-level retrieval system in the chat pipeline.** Despite claims of "RAG-style retrieval" in docstrings, the active chat implementation concatenates **all pages** of an uploaded document directly into the prompt context for Ollama (`qwen3:4b`).
2. An auxiliary page-level keyword function (`_find_relevant_pages`) exists in `chat_service.py`, but it is **dead code in production** (called only by regression unit tests).
3. The LEDGAR project (`LEDGAR_DeBERTa_Project`) and its integration (`classifier_service.py`) are strictly a **closed-set 100-class sequence classification model** (`ModernBERT-large` exported weights under `pretrained_model/`). It classifies isolated clause strings into SEC exhibit label categories (e.g., `Confidentiality`, `Indemnifications`, `Governing Laws`). It is **not** a retriever, indexer, bi-encoder, or ranker.
4. **No query-to-correct-clause dataset, ground-truth retrieval annotations, or retrieval benchmark scripts exist** anywhere in the repository. The only test contract present is a single 2-page, 8-clause synthetic contract (`lexiguard_sample_contract.pdf` / `SAMPLE_PAGE_1` & `SAMPLE_PAGE_2`).
5. Because LEDGAR provides single-label isolated clause strings without document context or natural language queries, the failure mode *"correct contract retrieved, answer-bearing clause missed or misranked"* **cannot be reproduced or benchmarked without constructing a synthetic or annotated evaluation suite**.

---

## 1. Actual Question-to-Evidence Retrieval Pipeline Trace

Tracing the flow from user input to LLM generation across the codebase:

```
[HTTP POST /api/documents/{doc_id}/chat]
   │
   ▼  (lexiguard-ai/backend/app/api/documents.py: chat_with_document, lines 80-106)
Reads body: {"question": "..."}
Fetches doc from in-memory store: _documents_store[doc_id]
   │
   ▼  (lexiguard-ai/backend/app/services/chat_service.py: answer_document_question, lines 178-295)
Checks doc.pages:
   │
   ├──> Calls _build_page_context(doc) (chat_service.py: lines 20-38)
   │      - Iterates through ALL doc.pages in order
   │      - Strips text, truncates pages exceeding max_chars_per_page (3000 chars) with "..."
   │      - Concatenates into: "--- Page 1 ---\n{text}\n\n--- Page 2 ---\n{text}"
   │      - NO retrieval filtering is applied. NO clause chunking is applied.
   │
   ├──> Assembles Prompt String:
   │      system_prompt: Strict JSON generation instructions & rules (lines 204-214)
   │      prompt: "Document Text:\n{page_context}\n\nQuestion: {question}\n\nRespond with ONLY valid JSON..." (lines 216-230)
   │
   ├──> Calls ollama_client.generate(prompt=prompt, system_prompt=system_prompt, ...) (lines 233-239)
   │      - Model: settings.OLLAMA_MODEL ("qwen3:4b")
   │      - Parameters: temperature=0.1, num_predict=512, think=False, format="json"
   │
   ├──> Parses JSON & repairs truncated outputs (lines 247-280)
   ├──> Post-processing & Sanitization:
   │      - _sanitize_chat_answer(answer) (lines 122-159)
   │      - _validate_page_citations(sources, doc) (lines 76-119)
   │      - _deduplicate_citations(sources) (lines 162-175)
   │
   ▼
Returns dict: {"answer": str, "sources": [{"page": int, "excerpt": str, "excerpt_verified": bool}], "demo_mode": False}
```

### Exact Files and Functions:
- **API Entrypoint**: [`documents.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/api/documents.py#L80-L106) -> `chat_with_document()`
- **Pipeline Orchestrator**: [`chat_service.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/chat_service.py#L178-L295) -> `answer_document_question()`
- **Context Builder**: [`chat_service.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/chat_service.py#L20-L38) -> `_build_page_context()`
- **Auxiliary/Dead Function**: [`chat_service.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/chat_service.py#L41-L73) -> `_find_relevant_pages()` (never called in `answer_document_question`)
- **Evidence Passed to LLM**: The entire text of **all pages** in the document, formatted as page blocks up to 3,000 characters per page.

---

## 2. Retrieval, Ranking, and Indexing Method: Grounded Code Findings

| Method | Status in Codebase | Concrete Location / Evidence |
| :--- | :--- | :--- |
| **Semantic Search / Dense Embeddings** | **ABSENT** | Grep for `sentence_transformers`, `torch.cosine_similarity`, `faiss`, `chroma`, `qdrant` yields **0 occurrences** in backend logic. |
| **BM25 / Sparse Retrieval** | **ABSENT** | Grep for `bm25` or `rank_bm25` yields **0 occurrences**. |
| **FAISS / Vector Index** | **ABSENT** | No vector database or index file exists in the workspace. |
| **Cross-Encoder Reranking** | **ABSENT** | Grep for `rerank` or `CrossEncoder` yields **0 occurrences**. |
| **Classifier-Assisted Retrieval** | **ABSENT** | The LEDGAR classifier is used **only** during static document analysis in [`analysis_service.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/analysis_service.py#L381-L417) to attach category labels (e.g., `Confidentiality (2. Confidentiality)`) to UI cards. It is **never called or consulted during chat Q&A**. |
| **Naive Lexical Scoring** | **INACTIVE (Unit-test only)** | [`chat_service.py: _find_relevant_pages()`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/chat_service.py#L41-L73): Simple token set overlap ($score = \sum 1_{kw \in page}$) filtered by a static 26-word stopword list. This function is **not invoked** by `answer_document_question()`. |
| **Actual Method Used** | **Full-Text In-Context Stuffing** | All document pages are concatenated into a single string (`_build_page_context`) and passed directly into the LLM prompt. |

---

## 3. Confidence Scores, Thresholds, Fallbacks, Verification, and Abstention

### A. Confidence Scores & Thresholds
- **In Chat (`chat_service.py`)**:
  - **No retrieval confidence score exists.**
  - **No relevance threshold exists.**
  - Stopword filtering in `_find_relevant_pages()` has a fixed threshold of `len(word) >= 3`.
  - Excerpt verification in `_validate_page_citations()` has a threshold: string substring check requires `len(excerpt) >= 6`.
  - Excerpt deduplication in `_deduplicate_citations()` uses `len(tokens) >= 8` and limits citations to a hardcoded maximum of 2.
- **In Document Risk Prioritization (`risk_prioritization_service.py`)**:
  - Multi-factor priority score: $Score = 100 \times ((0.45 \cdot S + 0.30 \cdot F + 0.25 \cdot O) \times E)$.
  - Evidence Grounding multiplier ($E$): `1.0` if verified with page reference; `0.90` if verified unpaginated; `0.50` if unverified in doc text; `0.40` if $< 15$ chars; `0.30` if missing.
- **In LEDGAR Classifier (`legal_clause_classifier.py`)**:
  - Softmax probabilities over 100 logits: `F.softmax(logits, dim=-1)`. Returns top 3 confidences (e.g., `0.9821`), but no rejection threshold is enforced.

### B. Fallback Logic
- **JSON Parse Failure**:
  - In `chat_service.py` (lines 254-260): If JSON parsing fails, sequentially tries appending suffixes `[']}', '"]}', '"}', '}']` to repair truncated JSON.
  - If still invalid, falls back to stripping Markdown fences (`clean_raw = re.sub(r"^```(?:json)?...", response_text)`).
- **Page Mismatch Fallback**:
  - In `_validate_page_citations()` (lines 105-114): If Ollama cites Page 2 but the excerpt actually occurs on Page 1, the system scans all pages, corrects the citation to Page 1, and marks `excerpt_verified = True`. If not found anywhere, `excerpt_verified` is set to `False`.

### C. Retries & Verification
- **LLM Retries**: **0 retries**. Network exceptions (`TimeoutError`, `httpx.HTTPError`) immediately fail with HTTP 504 or 500 without retry loops.
- **Evidence Verification**: Substring matching: `excerpt.lower() in page_text.lower()`.

### D. Abstention Behavior
- **Document Empty**: If `doc.pages` has no text, returns:
  `"No text has been extracted from this document. Please ensure the PDF contains selectable text."`
- **System Prompt Rule 5**: Prompts Ollama: `"If the document text does not contain the answer, state clearly: 'The provided document does not contain information regarding [topic].'"`
- **Post-Sanitization Fallback**: If Ollama output collapses to empty text after removing `<think>` tags and prompt echoes, defaults to:
  `"The provided document does not contain explicit provisions addressing this question."`

---

## 4. Query-to-Clause Dataset, Labels, and Evaluation Scripts

### A. Existing Datasets & Ground Truth
- **Query-to-Clause QA Pairs**: **None**. There is no dataset pairing natural language queries to ground-truth clause IDs, page spans, or text excerpts.
- **LEDGAR Dataset (`lighteval/lexglue`, config `ledgar`)**:
  - Schema: `{"text": "...", "label": int, "gold": ["Clause Category Name"]}`.
  - Size: 60,000 train / 10,000 val / 10,000 test.
  - **Crucial distinction**: These labels are single-label legal categorization tags (e.g., classifying a paragraph as `Severability` or `Notices`). They do **NOT** link questions to answer-bearing clauses.
- **Local Synthetic Contract**:
  - [`test_sample_contract_regression.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/tests/test_sample_contract_regression.py): Hardcodes 1 synthetic contract text with 8 sections.
  - [`test_chat_regression.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/tests/test_chat_regression.py): Contains two hardcoded test questions:
    - `"What are the payment terms and penalties for late payment?"` (targets Page 1 / Section 3)
    - `"How should notices be delivered?"` (targets Page 2 / Section 8)
  - This is a sanity unit test, not an evaluation benchmark.

### B. Existing Evaluation Scripts
- [`evaluate.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/LEDGAR_DeBERTa_Project/evaluate.py) in `LEDGAR_DeBERTa_Project`:
  - Evaluates sequence classification accuracy, macro-F1, and weighted-F1 of DeBERTa/ModernBERT on LEDGAR test set.
  - Contains **no retrieval metrics** (e.g., Hit@K, MRR@K, Recall@K, Precision@K, NDCG).
- No evaluation script exists in `lexiguard-ai` for retrieval or Q&A quality.

---

## 5. Reproducibility of the Target Failure Mode

**Target Failure**: *"Correct contract retrieved, answer-bearing clause missed or misranked."*

### Can this failure currently be reproduced using existing data?
**NO.** It cannot be reproduced or evaluated in the current repository state for two reasons:

1. **Architectural Reason**: The current system never retrieves or ranks clauses for Q&A. Because the full contract text is dumped into the LLM prompt, a clause cannot be "missed or misranked by retrieval" when no retriever is executing.
2. **Data Reason**: There is no evaluation corpus consisting of `(Contract, User Query, Ground-Truth Clause ID/Span, Ground-Truth Answer)`.

### Exactly What Data is Missing:
To reproduce, measure, and benchmark this failure mode, the following assets are required:
1. **Multi-Clause Document Set**: A collection of contracts segmented into discrete clauses (can be formed by grouping LEDGAR clauses into multi-clause synthetic contracts, or using segmented agreements).
2. **Query Suite**: A curated set of legal queries covering diverse question types:
   - *Direct factual* (e.g., "What is the liability cap?")
   - *Cross-referencing/conditional* (e.g., "Under what conditions can the provider terminate without cause?")
   - *Absence/unaddressed* (e.g., "What is the warranty period for hardware?") to test abstention.
3. **Ground-Truth Retrieval Map**: Explicit mapping from `Query_i` $\to$ `[Clause_ID_j, ...]`.
4. **Distractor Pool**: Non-relevant or superficially similar clauses within the same contract (e.g., `Payment Terms` vs. `Taxes and Invoicing` vs. `Audit Rights`) to create realistic misranking pressure.

---

## 6. Mapping Proposed Failure Types to Feasible Recovery Actions

| Proposed Failure Type | Concrete Root Cause in Legal Domain | Feasible Targeted Recovery Action | Smallest Implementation in LexiGuard |
| :--- | :--- | :--- | :--- |
| **1. Relevant clause missing from retrieved candidates** | Vocabulary mismatch (e.g., query asks for "late fee", contract uses "overdue interest accrual"); dense retriever embedding misses domain terminology. | **Hybrid Retrieval with Query Expansion**: Combine dense retrieval with lexical BM25; expand query with legal synonyms (or LEDGAR predicted category terms). | Split document using existing `chunk_document_into_candidate_clauses()`; retrieve top-$k$ via BM25 + dense embedding score. If max score $<\tau_{miss}$, expand query with LEDGAR category keywords. |
| **2. Relevant clause present but ranked too low** | Distractor clauses share generic legal boilerplate; top-$k$ cutoff drops the operative clause (e.g., ranked at position 6 when $k=3$). | **Category-Constrained Reranking / Cross-Encoder**: Rerank top-$M$ ($M > k$) using cross-encoder or LEDGAR clause classification prior to boost clauses whose predicted category matches the query intent. | Pull top-$M=8$ clauses; compute relevance score combined with classifier category alignment; rerank to top-$k=3$. |
| **3. Relevant clause retrieved without necessary context** | Clause depends on an adjacent definition, cross-referenced section (e.g., "subject to Section 4.2"), or schedule/exhibit. | **Parent-Child Chunking / Cross-Reference Expansion**: Detect explicit section references (regex: `Section \d+`, `Exhibit [A-Z]`) or retrieve windowed parent passage ($[\text{Clause}_{i-1}, \text{Clause}_i, \text{Clause}_{i+1}]$). | If retrieved clause contains regex `r"(?:Section\|Article\|Clause)\s+(\d+)"`, automatically fetch and append the referenced clause into the context. |
| **4. Retrieved evidence does not support the answer** | LLM hallucinates an answer or extrapolates beyond the retrieved snippet; or retrieved clause is irrelevant/silent on the topic. | **Post-Retrieval Evidence Gate & Abstention**: Verify that answer claims map to exact tokens in the evidence; if retriever confidence is below threshold $\tau_{abstain}$, trigger strict abstention. | Reuse existing `_validate_page_citations()` logic: if 0 citations pass exact verification, discard candidate answer and return the standard abstention message. |

---

## 7. Recommended Minimal Viable Mechanism & Evaluation Plan

### A. The Smallest Technically Feasible Mechanism
Do **not** build a massive, complex multi-agent framework. Instead, implement a **Failure-Aware Clause Retriever (FACR)** directly bridging the existing chunking engine and the LEDGAR classifier:

1. **Clause Indexer**:
   - In `chat_service.py`, replace `_build_page_context(doc)` with `chunk_document_into_candidate_clauses(doc)` (already implemented in `analysis_service.py:288-379`).
2. **Hybrid Top-$K$ Retrieval**:
   - Implement sparse BM25 + query-clause lexical overlap over candidate clauses.
3. **Failure Detection & Targeted Recovery**:
   - **Check 1 (Low Confidence / Missed Clause)**: If top clause score $< \tau$, classify the query into one of the 100 LEDGAR categories using the loaded `classifier_service` and retrieve clauses whose predicted category matches.
   - **Check 2 (Context Deficiency)**: If retrieved clause contains a cross-reference regex `r"(?:Section|Article|Clause)\s+(\d+)"`, retrieve the referenced clause ID into the evidence context.
   - **Check 3 (Support Verification / Abstention)**: If top score $< \tau_{abstain}$ and category match is absent, abstain immediately: *"The provided document does not contain information regarding [topic]."*

### B. Evaluation Plan Against Baseline and Ablations

#### 1. Baseline & Ablation Configurations
- **Baseline 1 (Current System)**: Full-Text Context Stuffing (dump all pages into LLM prompt).
- **Baseline 2**: Standard dense/BM25 Clause Retrieval (top-$k$ clauses without failure recovery).
- **Ablation A**: Standard Retrieval + Cross-Reference Context Expansion (evaluating context failure recovery).
- **Ablation B**: Standard Retrieval + LEDGAR Category-Guided Recovery (evaluating missed/misranked clause recovery).
- **Proposed Full System (FACR)**: Standard Retrieval + LEDGAR Recovery + Context Expansion + Verification Gate.

#### 2. Quantitative Metrics
- **Retrieval Performance**:
  - `Hit@1`, `Hit@3`, `Hit@5` (Is the answer-bearing clause in the top-$k$?)
  - `MRR` (Mean Reciprocal Rank)
  - `Context Completeness` (% of required cross-referenced clauses included)
- **Downstream QA Performance**:
  - `Exact Match (EM)` / `Token F1` of extracted entities (e.g., dates, amounts, percentages)
  - `Citation Precision`: % of cited excerpts that actually support the stated facts
  - `Abstention Accuracy`: Correct abstention rate on unanswerable/out-of-scope questions without hallucinations.

---

## 8. Test and Evaluation Artifacts Audit

| Artifact / Test File | Type | Implementation Status | Findings & Grounding |
| :--- | :--- | :--- | :--- |
| [`test_chat_regression.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/tests/test_chat_regression.py) | Unit / Regression | **Verified Implementation** | Tests document isolation, mock Q&A generation, citation validation, and anti-repetition. Note: `_find_relevant_pages` is tested here (lines 123-138) but is **dead code in the actual service**. |
| [`test_sample_contract_regression.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/tests/test_sample_contract_regression.py) | Unit / Regression | **Verified Implementation** | Tests dual-pass regex clause chunking (`chunk_document_into_candidate_clauses`) on the 8-clause sample contract. Verified working. |
| [`test_risk_prioritization.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/tests/test_risk_prioritization.py) | Unit / Regression | **Verified Implementation** | Tests deterministic risk scoring and evidence grounding multiplier ($E$). Verified working. |
| [`test_ai_integration.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/tests/test_ai_integration.py) | Integration | **Verified Implementation** | Tests Ollama client configuration, thinking-tag sanitization, and demo fallback. |
| [`evaluate.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/LEDGAR_DeBERTa_Project/evaluate.py) | Evaluation Script | **Verified Implementation** | Tests sequence classification metrics on LEDGAR test set. Contains **zero retrieval code**. |
| `test_evaluation_results.json` | Artifact | **Unverified / Absent** | Referenced in `evaluate.py` line 85 as the target output file, but does not currently exist on disk in `LEDGAR_DeBERTa_Project/results/`. |
| `observed_synthetic_outputs.json` | Artifact | **Verified Implementation** | In `pretrained_model/`: 4 synthetic test cases verifying local CPU inference of ModernBERT clause classifier. |

---

## 9. Concrete Separation of System Capabilities

To maintain rigorous research and engineering standards, project capabilities are strictly classified into three categories:

### A. Verified Implementation (Active in Code)
- Dual-pass regex clause segmentation (`chunk_document_into_candidate_clauses` in `analysis_service.py`).
- Pretrained 100-class clause classifier (`legal_clause_classifier.py` using local `ModernBERT-large` weights).
- Multi-factor explainable risk prioritization with evidence confidence penalty (`risk_prioritization_service.py`).
- Full-page document context assembly for Ollama Q&A (`chat_service.py`).
- Post-generation citation page validation and excerpt substring verification (`_validate_page_citations` in `chat_service.py`).

### B. Proposed Functionality (Target of Proposed Research)
- Clause-level query indexing and vector/BM25 retrieval.
- Categorization-guided query expansion / fallback retrieval using the LEDGAR classifier.
- Cross-reference clause dependency detection and windowed context recovery.
- Retrieval confidence scoring and threshold-based abstention.
- Evaluation harness tracking `Hit@K`, `MRR`, and `Citation Precision`.

### C. Unverified Assumptions (To Avoid)
- **Do not assume LEDGAR is a retrieval dataset**: LEDGAR labels are SEC exhibit classifications, not query-to-clause ground truth.
- **Do not assume the current app performs RAG**: The current app performs full-text document prompt injection.
- **Do not assume DeBERTa is running in `pretrained_model/`**: `model_reference.json` and `config.json` confirm the local checkpoint is `ModernBertForSequenceClassification` (`ModernBERT-large`, 1.58 GB `model.safetensors`), despite the folder and script naming.
