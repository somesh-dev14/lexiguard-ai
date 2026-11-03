# Evaluation run

- Started: 2026-10-25T15:11:04
- Data: `C:\Users\warso\Downloads\legal_ai_analyzer\lexiguard-ai\eval\data\lbrag` (200 questions)
- Source: LegalBench-RAG (Pipitone & Alami, 2024, arXiv:2408.10343)
- Setting: within-document retrieval: each question searches only the clauses of its own contract
- A gold span counts as retrieved when the top-k clauses cover >= 50% of it
- Dataset warnings: 0; gold spans crossing clause boundaries: 103
- Model load errors: none

## Retrieval (answerable questions)

| variant | n | mrr | hit@1 | hit@3 | hit@5 | hit@10 | complete@1 | complete@3 | complete@5 | complete@10 | char_recall@1 | char_recall@3 | char_recall@5 | char_recall@10 | char_precision@1 | char_precision@3 | char_precision@5 | char_precision@10 | primary_recall@1 | primary_recall@3 | primary_recall@5 | primary_recall@10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 200 | 0.3891 | 0.28 | 0.46 | 0.555 | 0.62 | 0.225 | 0.36 | 0.43 | 0.5 | 0.2493 | 0.4109 | 0.4943 | 0.5692 | 0.1907 | 0.1112 | 0.0925 | 0.0747 | 0.2033 | 0.3367 | 0.4167 | 0.5 |
| hybrid | 200 | 0.4447 | 0.315 | 0.53 | 0.62 | 0.715 | 0.255 | 0.415 | 0.49 | 0.625 | 0.2826 | 0.4684 | 0.5545 | 0.6739 | 0.2098 | 0.1316 | 0.1025 | 0.078 | 0.2233 | 0.4 | 0.4867 | 0.5967 |

### Equal text budget (what fits in the prompt)

| variant | budget4000_char_precision | budget4000_char_recall | budget4000_chars | budget4000_clauses | budget4000_complete | budget8000_char_precision | budget8000_char_recall | budget8000_chars | budget8000_clauses | budget8000_complete | budget12000_char_precision | budget12000_char_recall | budget12000_chars | budget12000_clauses | budget12000_complete |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 0.0823 | 0.5075 | 2997.3 | 6.0 | 0.435 | 0.0696 | 0.5909 | 5195.8 | 10.1 | 0.54 | 0.067 | 0.629 | 6782.9 | 13.2 | 0.585 |
| hybrid | 0.0885 | 0.5671 | 3325.6 | 6.9 | 0.505 | 0.0691 | 0.6987 | 6195.4 | 12.5 | 0.665 | 0.0578 | 0.7475 | 8677.3 | 17.6 | 0.72 |

### complete@k by question type

| variant | type | n | complete@1 | complete@3 | complete@5 | complete@10 |
|---|---|---|---|---|---|---|
| bm25 | contractnli | 50 | 0.48 | 0.7 | 0.76 | 0.88 |
| bm25 | cuad | 50 | 0.32 | 0.46 | 0.56 | 0.6 |
| bm25 | maud | 50 | 0.0 | 0.04 | 0.04 | 0.04 |
| bm25 | privacy_qa | 50 | 0.1 | 0.24 | 0.36 | 0.48 |
| hybrid | contractnli | 50 | 0.44 | 0.66 | 0.74 | 0.88 |
| hybrid | cuad | 50 | 0.42 | 0.56 | 0.58 | 0.74 |
| hybrid | maud | 50 | 0.02 | 0.02 | 0.04 | 0.08 |
| hybrid | privacy_qa | 50 | 0.14 | 0.42 | 0.6 | 0.8 |


## Baseline (full-document prompt) coverage

- skipped: dataset has no page layout; the baseline's per-page cut cannot be reproduced

_Small or synthetic datasets only show whether the pipeline works, not whether one method is better._
