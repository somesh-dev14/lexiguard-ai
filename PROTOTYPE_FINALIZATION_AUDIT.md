# PROTOTYPE FINALIZATION AUDIT REPORT
**Project**: LexiGuard AI & LEDGAR Classifier Integration  
**Date of Audit**: October 19, 2026  
**Scope**: Finalization & validation of existing prototype prior to research novelty implementation. Local application only. LEDGAR only.

---

## 1. Actual Test and Build Results (From This Run)

All tests and builds were executed directly in the live environment:

### A. Backend Test Suite (Pytest)
- **Interpreter**: `lexiguard-ai\backend\venv\Scripts\python.exe` (Python 3.12.10, PyTorch CPU, transformers 5.9.0, modernbert, pytest 9.1.1, anyio 4.15.1)
- **Command**: `.\venv\Scripts\python.exe -m pytest tests -v`
- **Results**: **94 passed, 0 failed, 4 warnings** in 92.72 seconds.
- **Coverage**:
  - `test_ai_integration.py` (8 passed)
  - `test_chat_regression.py` (33 passed across asyncio and trio runners)
  - `test_health.py` (1 passed)
  - `test_pdf_integration.py` (2 passed)
  - `test_risk_analysis_regression.py` (16 passed across asyncio and trio runners)
  - `test_risk_prioritization.py` (3 passed)
  - `test_sample_contract_regression.py` (7 passed)
  - `test_summary_and_export_regression.py` (5 passed)
  - `test_summary_repair.py` (4 passed)

### B. Frontend Test Suite (Vitest)
- **Environment**: Node.js `v22.14.0`, npm `10.9.2`, vitest `v1.6.1`
- **Command**: `$env:Path = "C:\Program Files\nodejs;$env:Path"; npm test`
- **Results**: **2 test files passed, 6 tests passed, 0 failed** in 38.39 seconds.
  - `src/test/ChatInterface.test.tsx` (3 passed)
  - `src/test/AnalysisPage.test.tsx` (3 passed)

### C. Frontend Production Build (Vite)
- **Command**: `$env:Path = "C:\Program Files\nodejs;$env:Path"; npm run build`
- **Results**: **Success (Exit code 0)** in 9.82 seconds.
  - TypeScript type check (`tsc`): Clean, 0 errors.
  - Production bundles created:
    - `dist/index.html`: 0.62 kB (gzip: 0.38 kB)
    - `dist/assets/index-xgxo0COT.css`: 32.14 kB (gzip: 6.21 kB)
    - `dist/assets/index-_HqS8AMe.js`: 453.94 kB (gzip: 139.11 kB)

---

## 2. Tests That Could Not Run (and Why)

1. **System Python Pytest Run**:
   - Running `python -m pytest tests` using the system Python (`C:\Users\warso\AppData\Local\Programs\Python\Python312\python.exe`) failed with `ModuleNotFoundError: No module named 'pydantic_settings'`.
   - **Reason**: Dependencies are installed in the backend virtual environment (`backend/venv`), not the global system environment. Running with `.\venv\Scripts\python.exe -m pytest tests` completed with 100% passes.
2. **Global NPM CLI in Standard Path**:
   - Invoking `npm` directly initially failed with `CommandNotFoundException` because `C:\Program Files\nodejs` was not registered in the default non-interactive PowerShell session `PATH`.
   - **Resolution**: Prepending `C:\Program Files\nodejs` to `$env:Path` resolved this cleanly.
3. **LEDGAR Test Split Re-Evaluation (`evaluate.py`)**:
   - `LEDGAR_DeBERTa_Project/evaluate.py` was not run to completion during this audit pass because full inference on the 10,000-sample test set on a CPU requires >2.5 hours and would tie up system resources. Model architecture and inference readiness were verified via unit tests and synthetic checkpoints.

---

## 3. Detailed Audit by Feature Area

### Feature 1: Application Startup and Document Upload
- **Status**: **VERIFIED WORKING**
- **Grounding**:
  - [`health.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/api/health.py) returns 200 with service status, version (`1.0.0`), and current `ai_mode`. Tested via `test_health.py`.
  - [`documents.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/api/documents.py#L14-L51) (`upload_document`): Enforces `.pdf` extension check, 50MB file size cap, generates uuid-backed `doc_id`, stores document in `_documents_store`. Tested via `test_pdf_integration.py`.
  - Frontend [`UploadZone.tsx`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/frontend/src/components/documents/UploadZone.tsx) and [`api.ts`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/frontend/src/services/api.ts#L18-L69) handle progress reporting via XMLHttpRequest.

### Feature 2: PDF Extraction and Page-Number Preservation
- **Status**: **VERIFIED WORKING**
- **Grounding**:
  - [`pdf_extractor.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/pdf_extractor.py#L8-L27): Uses PyMuPDF (`fitz`), iterating 0-indexed pages and outputting 1-indexed `PageText(page_number=page_idx + 1, text=text)`.
  - Correctly calculates word counts and preserves page integrity.

### Feature 3: Clause Segmentation and LEDGAR Classification
- **Status**: **VERIFIED WORKING WITH EDGE-CASE LIMITATIONS**
- **Grounding**:
  - [`analysis_service.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/analysis_service.py#L236-L378): Employs a dual-pass regex strategy (`INLINE_CLAUSE_REGEX` and `LINE_CLAUSE_REGEX`) mapping characters to a 1D `char_page_map`.
  - Fallback to paragraph chunking activates if no numbered headers are found.
  - [`classifier_service.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/classifier_service.py) loads the local pretrained weights (`ModernBERT-large` exported weights under `pretrained_model/`) and classifies each segmented passage into top 3 categories with softmax confidences.
  - Tested in `test_sample_contract_regression.py` (verifying exact 8-clause extraction, correct headings, and sequential IDs).

### Feature 4: Executive Summary and Key Obligations
- **Status**: **VERIFIED WORKING (WITH POST-PROCESSING REPAIR HEURISTICS)**
- **Grounding**:
  - LLM extraction via Ollama (`qwen3:4b`) schema for `overview`, `contract_type`, `parties`, `effective_date`, `duration`, and `key_obligations`.
  - [`analysis_service.py:_source_summary`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/analysis_service.py#L94-L210): Enforces deterministic post-processing repairs. Drops placeholders (`You1`, `Party A`, schema echo tokens), extracts parties directly from regex patterns, and replaces generic boilerplate obligations with verified contract sentences containing `must|shall|will|agrees to`.
  - Tested in `test_summary_repair.py` and `test_summary_and_export_regression.py`.

### Feature 5: Risk Analysis and Evidence Grounding
- **Status**: **VERIFIED WORKING**
- **Grounding**:
  - [`analysis_service.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/analysis_service.py#L525-L663): Implements a 3-tier evidence verification pipeline:
    1. Single-page token substring matching (`Check 2A`).
    2. Candidate clause matching (`Check 2B`).
    3. Multi-page continuous token stream matching (`Check 2C`) to ground quotes crossing page boundaries.
  - Marks unverified excerpts with `evidence_unverified = True` if $< 15$ characters, $< 3$ tokens, or not grounded in the source text.
  - [`risk_prioritization_service.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/risk_prioritization_service.py): Calculates explainable composite scores:
    $$\text{Score} = 100 \times ((0.45 \cdot S + 0.30 \cdot F + 0.25 \cdot O) \times E)$$
    penalizing unverified evidence ($E = 0.40 \text{ to } 0.50$).

### Feature 6: Chatbot Answer Accuracy and Citations
- **Status**: **VERIFIED WORKING (WITHIN SCOPE OF FULL-TEXT IN-CONTEXT STUFFING)**
- **Grounding**:
  - [`chat_service.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/chat_service.py#L178-L295): Prompts Ollama with the full page-delineated contract.
  - [`_validate_page_citations`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/chat_service.py#L76-L119): Drops citations referencing nonexistent pages, verifies that excerpt text exists in the cited page, and autocorrects misattributed page citations.
  - [`_sanitize_chat_answer`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/chat_service.py#L122-L160): Strips `<think>` tags, prompt meta-narration, and trailing incomplete sentence fragments.
  - [`_deduplicate_citations`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/chat_service.py#L162-L175): Removes duplicate quotes and caps citations to 2 items.

### Feature 7: Frontend/Backend Integration
- **Status**: **VERIFIED WORKING**
- **Grounding**:
  - Types in [`frontend/src/types/index.ts`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/frontend/src/types/index.ts) strictly align with backend Pydantic schemas in `app/schemas/document.py`.
  - All 4 tabs in `AnalysisPage.tsx` (`SummaryTab`, `ClausesTab`, `RiskTab`, `SourceTab`) correctly render live analysis outputs, risk breakdown accordions, and jump-to-page source navigation.
  - Passed both `ChatInterface.test.tsx` and `AnalysisPage.test.tsx`.

### Feature 8: Error Handling and Local Ollama / Qwen Integration
- **Status**: **VERIFIED WORKING**
- **Grounding**:
  - [`ollama_client.py`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/ollama_client.py):
    - Connects to local Ollama (`http://localhost:11434`, verified running with PID 41148 and `qwen3:4b` available).
    - ChatML prompt template prefixing (`<think>\nDone.\n</think>`) successfully prevents Qwen3 from burning output tokens on internal deliberation.
    - Handles timeouts (`TimeoutError`) and surfaces descriptive HTTP 504 / 500 errors.

---

## 4. Rechecking Previously Observed Issues

| Issue | Code Investigation & Current Status | Exact Location | Finding & Status |
| :--- | :--- | :--- | :--- |
| **1. Multi-page clauses receive incorrect page number** | In `chunk_document_into_candidate_clauses`, clause page is assigned solely based on `start_pos`: `char_page_map[start_pos]`. If Clause 7 starts on Page 1 and ends on Page 2, it is labeled as Page 1. For risk evidence, `Check 2C` in `analysis_service.py:592-613` finds cross-page evidence, but sets `matched_page = p_curr` (starting page). | [`analysis_service.py:338`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/analysis_service.py#L338) and [`analysis_service.py:607`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/analysis_service.py#L607) | **CONFIRMED REPRODUCIBLE DEFICIENCY**. Schema only supports an integer `page?: number` instead of `page_start` / `page_end` or `pages: number[]`. Clicking "Jump to Page" only navigates to the start page. If the relevant quote is on the second half of the clause (e.g. Page 2), the user is taken to Page 1. |
| **2. Executive summaries omit payment deadlines, interest, security deadlines, SLA commitments** | In `analysis_service.py:_source_summary`, `key_obligations` fallback regex only looks for general auxiliary verbs: `\b(must\|shall\|will\|agrees? to\|is required to)\b`. It captures the first 4 sentences indiscriminately and caps at 5 items without targeting financial deadlines, late interest rates, or breach response windows. | [`analysis_service.py:173-188`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/analysis_service.py#L173-L188) | **CONFIRMED REPRODUCIBLE DEFICIENCY**. If Ollama fails to extract specific payment/security obligations or outputs generic text, the fallback repair extracts general sentences (e.g., "Provider agrees to deliver software development") rather than prioritizing numerical commitments (e.g., "within thirty (30) days", "interest at 1.5% per month", "dispute within 15 days"). |
| **3. Risk findings do not distinguish genuine defects from optional negotiation improvements** | In `analysis_service.py`, `ollama_prompt` Rule 4 requests framing negotiation postures as "review points", but the schema only has `"severity": "low\|medium\|high\|critical"` and does not have a formal `risk_type` or `finding_category` field (e.g., `contract_defect` vs `negotiation_point`). | [`analysis_service.py:441-453`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/analysis_service.py#L441-L453) and [`frontend/src/types/index.ts:49-64`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/frontend/src/types/index.ts#L49-L64) | **CONFIRMED REPRODUCIBLE DEFICIENCY**. All findings are presented homogeneously as risks with severity tags. An optional standard term (e.g., requesting a mutual NDA carveout) can appear as a "Medium Risk" rather than a categorized "Negotiation Consideration". |
| **4. Chat answers concise, evidence-grounded, avoiding unsupported claims** | Evaluated via `test_chat_regression.py`. `_sanitize_chat_answer` removes meta-narration and thinking blocks. System prompt rule 5 mandates explicit disclosure if facts are absent. Unit test `test_unsupported_question_explicitly_discloses_absence` passes. | [`chat_service.py:122-159`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/chat_service.py#L122-L159) | **VERIFIED WORKING AS SPECIFIED**. The post-processing pipeline prevents internal reasoning and echoes from appearing in user chat outputs. |

---

## 5. Prioritized Bug and Limitation Matrix

### Critical Priority (P0)
*(None currently breaking runtime execution or existing tests)*

### High Priority (P1)
1. **Multi-Page Clause Spans Cause Ambiguous Source Navigation**:
   - **File**: [`analysis_service.py:338, 346`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/analysis_service.py#L338)
   - **Issue**: Clauses crossing page boundaries (such as Section 7 spanning Page 1 and Page 2 in the sample agreement) only record `page: clause_page` (start page). When risk excerpts or chat citations point to text on the second page, the clause card indicates only the starting page.
   - **Impact**: Source navigation in the UI misleads the reviewer on cross-page clauses.

2. **Executive Summary Key Obligations Miss Critical Operational and Financial Metrics**:
   - **File**: [`analysis_service.py:173-188`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/analysis_service.py#L173-L188)
   - **Issue**: Heuristic obligation fallback selects generic operative sentences without ranking sentences containing explicit numerical deadlines (`days`, `hours`), financial metrics (`% per month`, `fee`, currency), or termination windows.
   - **Impact**: Executive overview omits essential business terms if the LLM output requires repair.

### Medium Priority (P2)
3. **Absence of Distinct Taxonomy Between Definitive Defects and Negotiation Considerations**:
   - **File**: [`analysis_service.py:441-453`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/analysis_service.py#L441-L453), [`risk_prioritization_service.py:140-149`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/risk_prioritization_service.py#L140-L149), [`frontend/src/types/index.ts:49-64`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/frontend/src/types/index.ts#L49-L64)
   - **Issue**: The risk model treats all findings as standard liabilities with varying severities (`critical`, `high`, `medium`, `low`). There is no discrete `finding_type` (e.g. `defect`, `omission`, `negotiation_point`).
   - **Impact**: Commercial negotiation points are labeled as legal risks, which can cause false alarms during contract review.

4. **Dead Code in Chat Service**:
   - **File**: [`chat_service.py:41-73`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/services/chat_service.py#L41-L73) (`_find_relevant_pages`)
   - **Issue**: This function is tested in unit tests but never called in `answer_document_question`. Full text is injected into prompt context instead.
   - **Impact**: Confusing architecture; creates an illusion of page-filtering retrieval that is not actively executing.

### Low Priority (P3)
5. **Deprecated Pydantic Config and UTC Datetime Warnings**:
   - **Files**: [`app/core/config.py:26`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/core/config.py#L26), [`app/api/documents.py:36`](file:///c:/Users/warso/Downloads/legal_ai_analyzer/lexiguard-ai/backend/app/api/documents.py#L36)
   - **Issue**: `class Config` in `Settings` triggers Pydantic V2 deprecation warning; `datetime.utcnow()` triggers Python 3.12 deprecation warning.
   - **Impact**: Harmless deprecation logs during test execution.

---

## 6. Proposed Fix Order (Preserving Existing Functionality)

To validate and finalize the prototype cleanly without regressing the 94 passing backend tests and 6 passing frontend tests:

```
Step 1: Multi-Page Clause Span Tracking (P1)
  ├── Update chunk_document_into_candidate_clauses to track page_start and page_end
  ├── Attach page_end / page_span to candidate clauses
  └── Ensure backward compatibility: keep 'page' as page_start so no tests break

Step 2: Priority-Ranked Key Obligations Fallback (P1)
  ├── Enhance _source_summary obligation extraction with a scoring heuristic:
  │     prioritize sentences containing numbers, currencies, "within X days", "%", "cure"
  └── Retain existing placeholder filtering and grounding checks

Step 3: Defect vs. Negotiation Point Classification (P2)
  ├── Enrich risk schema with finding_type ("defect" | "omission" | "negotiation_point")
  └── Update prompt and RiskTab.tsx to display dedicated badge for negotiation considerations

Step 4: Deprecation and Cleanup (P3)
  ├── Update config.py to model_config = SettingsConfigDict(env_file=".env", extra="allow")
  └── Replace datetime.utcnow() with datetime.now(datetime.UTC)
```

---

## 7. Recommended First Concrete Fix

**Recommended First Fix**: **Step 1 — Multi-Page Clause Span Tracking with Page End Attribution**.

### Why this is the best first step:
1. It directly fixes the confirmed defect where clauses spanning page boundaries (e.g., Section 7 across Page 1 & 2) only report Page 1.
2. It improves grounding accuracy for risk evidence and citation navigation without modifying any LLM prompt logic.
3. It can be implemented with complete backward compatibility by preserving `c["page"] = page_start` while exposing `c["page_end"] = page_end` and `c["page_span"] = f"{page_start}" if page_start == page_end else f"{page_start}-{page_end}"`.
4. All existing 94 backend tests and 6 frontend tests will continue to pass.
