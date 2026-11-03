# Evaluation run

- Started: 2026-10-25T14:18:41
- Data: `C:\Users\warso\Downloads\legal_ai_analyzer\lexiguard-ai\eval\data\lbrag` (200 questions)
- Source: LegalBench-RAG (Pipitone & Alami, 2024, arXiv:2408.10343)
- Setting: within-document retrieval: each question searches only the clauses of its own contract
- A gold span counts as retrieved when the top-k clauses cover >= 50% of it
- Dataset warnings: 0; gold spans crossing clause boundaries: 57
- Model load errors: none

## Retrieval (answerable questions)

| variant | n | mrr | hit@1 | hit@3 | hit@5 | hit@10 | complete@1 | complete@3 | complete@5 | complete@10 | char_recall@1 | char_recall@3 | char_recall@5 | char_recall@10 | char_precision@1 | char_precision@3 | char_precision@5 | char_precision@10 | primary_recall@1 | primary_recall@3 | primary_recall@5 | primary_recall@10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 200 | 0.4571 | 0.34 | 0.54 | 0.645 | 0.7 | 0.28 | 0.46 | 0.545 | 0.65 | 0.3062 | 0.5012 | 0.5965 | 0.6755 | 0.1671 | 0.0931 | 0.0801 | 0.0639 | 0.2533 | 0.4267 | 0.53 | 0.6233 |
| hybrid | 200 | 0.5218 | 0.375 | 0.645 | 0.715 | 0.795 | 0.285 | 0.515 | 0.63 | 0.76 | 0.3279 | 0.5858 | 0.6703 | 0.7802 | 0.1855 | 0.1095 | 0.0869 | 0.063 | 0.2833 | 0.53 | 0.6133 | 0.7133 |
| hybrid+rerank | 200 | 0.5515 | 0.425 | 0.635 | 0.71 | 0.8 | 0.33 | 0.51 | 0.62 | 0.755 | 0.3763 | 0.5693 | 0.6679 | 0.7785 | 0.2061 | 0.1061 | 0.0843 | 0.0635 | 0.31 | 0.5067 | 0.61 | 0.7267 |

### Equal text budget (what fits in the prompt)

| variant | budget4000_char_precision | budget4000_char_recall | budget4000_chars | budget4000_clauses | budget4000_complete | budget8000_char_precision | budget8000_char_recall | budget8000_chars | budget8000_clauses | budget8000_complete | budget12000_char_precision | budget12000_char_recall | budget12000_chars | budget12000_clauses | budget12000_complete |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 0.0825 | 0.5024 | 3214.3 | 3.8 | 0.45 | 0.0679 | 0.6289 | 5790.6 | 6.3 | 0.59 | 0.0611 | 0.6627 | 7756.5 | 8.5 | 0.64 |
| hybrid | 0.0923 | 0.5995 | 3482.2 | 4.5 | 0.54 | 0.0699 | 0.7056 | 6485.5 | 7.7 | 0.675 | 0.0591 | 0.7685 | 9108.4 | 10.7 | 0.75 |
| hybrid+rerank | 0.0873 | 0.6032 | 3472.9 | 4.7 | 0.55 | 0.066 | 0.7238 | 6453.2 | 8.0 | 0.685 | 0.0584 | 0.7734 | 9067.3 | 11.0 | 0.74 |

### complete@k by question type

| variant | type | n | complete@1 | complete@3 | complete@5 | complete@10 |
|---|---|---|---|---|---|---|
| bm25 | contractnli | 50 | 0.5 | 0.76 | 0.92 | 1.0 |
| bm25 | cuad | 50 | 0.42 | 0.58 | 0.62 | 0.72 |
| bm25 | maud | 50 | 0.02 | 0.06 | 0.12 | 0.16 |
| bm25 | privacy_qa | 50 | 0.18 | 0.44 | 0.52 | 0.72 |
| hybrid | contractnli | 50 | 0.46 | 0.76 | 0.88 | 1.0 |
| hybrid | cuad | 50 | 0.5 | 0.64 | 0.72 | 0.84 |
| hybrid | maud | 50 | 0.02 | 0.02 | 0.1 | 0.24 |
| hybrid | privacy_qa | 50 | 0.16 | 0.64 | 0.82 | 0.96 |
| hybrid+rerank | contractnli | 50 | 0.46 | 0.66 | 0.84 | 1.0 |
| hybrid+rerank | cuad | 50 | 0.56 | 0.74 | 0.8 | 0.86 |
| hybrid+rerank | maud | 50 | 0.06 | 0.08 | 0.1 | 0.24 |
| hybrid+rerank | privacy_qa | 50 | 0.24 | 0.56 | 0.74 | 0.92 |


## Baseline (full-document prompt) coverage

- skipped: dataset has no page layout; the baseline's per-page cut cannot be reproduced

_Small or synthetic datasets only show whether the pipeline works, not whether one method is better._
