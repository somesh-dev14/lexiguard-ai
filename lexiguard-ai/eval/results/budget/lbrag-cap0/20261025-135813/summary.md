# Evaluation run

- Started: 2026-10-25T13:58:13
- Data: `C:\Users\warso\Downloads\legal_ai_analyzer\lexiguard-ai\eval\data\lbrag` (200 questions)
- Source: LegalBench-RAG (Pipitone & Alami, 2024, arXiv:2408.10343)
- Setting: within-document retrieval: each question searches only the clauses of its own contract
- A gold span counts as retrieved when the top-k clauses cover >= 50% of it
- Dataset warnings: 0; gold spans crossing clause boundaries: 12
- Model load errors: none

## Retrieval (answerable questions)

| variant | n | mrr | hit@1 | hit@3 | hit@5 | hit@10 | complete@1 | complete@3 | complete@5 | complete@10 | char_recall@1 | char_recall@3 | char_recall@5 | char_recall@10 | char_precision@1 | char_precision@3 | char_precision@5 | char_precision@10 | primary_recall@1 | primary_recall@3 | primary_recall@5 | primary_recall@10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 200 | 0.7234 | 0.645 | 0.775 | 0.825 | 0.9 | 0.585 | 0.725 | 0.795 | 0.865 | 0.6101 | 0.7511 | 0.8077 | 0.8794 | 0.1454 | 0.078 | 0.0629 | 0.0547 | 0.5867 | 0.7067 | 0.7667 | 0.85 |
| hybrid | 200 | 0.7206 | 0.625 | 0.78 | 0.865 | 0.92 | 0.575 | 0.695 | 0.805 | 0.885 | 0.6006 | 0.7412 | 0.8387 | 0.9088 | 0.1501 | 0.074 | 0.0612 | 0.0497 | 0.5733 | 0.7033 | 0.8033 | 0.8667 |
| hybrid+rerank | 200 | 0.7118 | 0.615 | 0.77 | 0.865 | 0.925 | 0.58 | 0.715 | 0.81 | 0.885 | 0.5924 | 0.745 | 0.8406 | 0.9078 | 0.1526 | 0.0799 | 0.0639 | 0.0499 | 0.5567 | 0.7067 | 0.8033 | 0.87 |

### Equal text budget (what fits in the prompt)

| variant | budget4000_char_precision | budget4000_char_recall | budget4000_chars | budget4000_clauses | budget4000_complete | budget8000_char_precision | budget8000_char_recall | budget8000_chars | budget8000_clauses | budget8000_complete | budget12000_char_precision | budget12000_char_recall | budget12000_chars | budget12000_clauses | budget12000_complete |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 0.0733 | 0.4841 | 3480.2 | 2.5 | 0.445 | 0.0645 | 0.6434 | 6365.9 | 3.8 | 0.61 | 0.0577 | 0.6905 | 8569.5 | 4.7 | 0.67 |
| hybrid | 0.0712 | 0.4856 | 3619.6 | 2.9 | 0.445 | 0.0595 | 0.6707 | 6715.1 | 4.7 | 0.64 | 0.0519 | 0.7162 | 9405.1 | 6.5 | 0.69 |
| hybrid+rerank | 0.0702 | 0.5214 | 3607.9 | 3.0 | 0.49 | 0.0569 | 0.6736 | 6691.0 | 4.8 | 0.65 | 0.0495 | 0.7239 | 9392.5 | 6.7 | 0.71 |

### complete@k by question type

| variant | type | n | complete@1 | complete@3 | complete@5 | complete@10 |
|---|---|---|---|---|---|---|
| bm25 | contractnli | 50 | 0.6 | 0.82 | 0.94 | 1.0 |
| bm25 | cuad | 50 | 0.48 | 0.74 | 0.8 | 0.88 |
| bm25 | maud | 50 | 0.28 | 0.36 | 0.46 | 0.6 |
| bm25 | privacy_qa | 50 | 0.98 | 0.98 | 0.98 | 0.98 |
| hybrid | contractnli | 50 | 0.5 | 0.66 | 0.92 | 1.0 |
| hybrid | cuad | 50 | 0.52 | 0.72 | 0.84 | 0.98 |
| hybrid | maud | 50 | 0.28 | 0.4 | 0.46 | 0.56 |
| hybrid | privacy_qa | 50 | 1.0 | 1.0 | 1.0 | 1.0 |
| hybrid+rerank | contractnli | 50 | 0.5 | 0.74 | 0.94 | 1.0 |
| hybrid+rerank | cuad | 50 | 0.6 | 0.82 | 0.96 | 0.98 |
| hybrid+rerank | maud | 50 | 0.22 | 0.3 | 0.34 | 0.56 |
| hybrid+rerank | privacy_qa | 50 | 1.0 | 1.0 | 1.0 | 1.0 |


## Baseline (full-document prompt) coverage

- skipped: dataset has no page layout; the baseline's per-page cut cannot be reproduced

_Small or synthetic datasets only show whether the pipeline works, not whether one method is better._
