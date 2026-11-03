# Evaluation run

- Started: 2026-10-25T13:53:41
- Data: `C:\Users\warso\Downloads\legal_ai_analyzer\lexiguard-ai\eval\data\lbrag` (200 questions)
- Source: LegalBench-RAG (Pipitone & Alami, 2024, arXiv:2408.10343)
- Setting: within-document retrieval: each question searches only the clauses of its own contract
- A gold span counts as retrieved when the top-k clauses cover >= 50% of it
- Dataset warnings: 0; gold spans crossing clause boundaries: 34
- Model load errors: none

## Retrieval (answerable questions)

| variant | n | mrr | hit@1 | hit@3 | hit@5 | hit@10 | complete@1 | complete@3 | complete@5 | complete@10 | char_recall@1 | char_recall@3 | char_recall@5 | char_recall@10 | char_precision@1 | char_precision@3 | char_precision@5 | char_precision@10 | primary_recall@1 | primary_recall@3 | primary_recall@5 | primary_recall@10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 200 | 0.5588 | 0.45 | 0.635 | 0.705 | 0.79 | 0.375 | 0.56 | 0.655 | 0.74 | 0.4136 | 0.5847 | 0.6681 | 0.7536 | 0.1605 | 0.0828 | 0.0699 | 0.0592 | 0.36 | 0.54 | 0.6267 | 0.7167 |
| hybrid | 200 | 0.5793 | 0.45 | 0.655 | 0.775 | 0.86 | 0.37 | 0.555 | 0.705 | 0.805 | 0.4135 | 0.5924 | 0.727 | 0.8268 | 0.1614 | 0.0831 | 0.0714 | 0.0548 | 0.3633 | 0.54 | 0.6867 | 0.78 |

### complete@k by question type

| variant | type | n | complete@1 | complete@3 | complete@5 | complete@10 |
|---|---|---|---|---|---|---|
| bm25 | contractnli | 50 | 0.6 | 0.82 | 0.94 | 1.0 |
| bm25 | cuad | 50 | 0.42 | 0.6 | 0.7 | 0.82 |
| bm25 | maud | 50 | 0.02 | 0.08 | 0.18 | 0.26 |
| bm25 | privacy_qa | 50 | 0.46 | 0.74 | 0.8 | 0.88 |
| hybrid | contractnli | 50 | 0.5 | 0.66 | 0.92 | 1.0 |
| hybrid | cuad | 50 | 0.46 | 0.6 | 0.74 | 0.9 |
| hybrid | maud | 50 | 0.02 | 0.16 | 0.22 | 0.32 |
| hybrid | privacy_qa | 50 | 0.5 | 0.8 | 0.94 | 1.0 |


## Baseline (full-document prompt) coverage

- skipped: dataset has no page layout; the baseline's per-page cut cannot be reproduced

_Small or synthetic datasets only show whether the pipeline works, not whether one method is better._
