# Evaluation run

- Started: 2026-10-25T13:51:24
- Data: `C:\Users\warso\Downloads\legal_ai_analyzer\lexiguard-ai\eval\data\contractnli` (510 questions)
- Source: ContractNLI (Koreeda & Manning, 2021), CC BY 4.0
- Setting: within-document retrieval: each question searches only the clauses of its own contract
- A gold span counts as retrieved when the top-k clauses cover >= 50% of it
- Dataset warnings: 0; gold spans crossing clause boundaries: 119
- Model load errors: none

## Retrieval (answerable questions)

| variant | n | mrr | hit@1 | hit@3 | hit@5 | hit@10 | complete@1 | complete@3 | complete@5 | complete@10 | char_recall@1 | char_recall@3 | char_recall@5 | char_recall@10 | char_precision@1 | char_precision@3 | char_precision@5 | char_precision@10 | primary_recall@1 | primary_recall@3 | primary_recall@5 | primary_recall@10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 291 | 0.5845 | 0.4502 | 0.6495 | 0.7801 | 0.9347 | 0.2646 | 0.4605 | 0.5979 | 0.7938 | 0.372 | 0.5651 | 0.6958 | 0.8631 | 0.2931 | 0.1664 | 0.125 | 0.0834 | 0.3041 | 0.5248 | 0.6509 | 0.8378 |
| hybrid | 291 | 0.5881 | 0.4227 | 0.6907 | 0.8385 | 0.9553 | 0.2543 | 0.5017 | 0.6564 | 0.8247 | 0.3447 | 0.6038 | 0.7547 | 0.8918 | 0.2602 | 0.1727 | 0.1312 | 0.0851 | 0.295 | 0.5586 | 0.705 | 0.8671 |

### complete@k by question type

| variant | type | n | complete@1 | complete@3 | complete@5 | complete@10 |
|---|---|---|---|---|---|---|
| bm25 | nli_contradiction | 52 | 0.2885 | 0.4615 | 0.6346 | 0.8077 |
| bm25 | nli_entailment | 239 | 0.2594 | 0.4603 | 0.59 | 0.7908 |
| hybrid | nli_contradiction | 52 | 0.25 | 0.4808 | 0.6923 | 0.8654 |
| hybrid | nli_entailment | 239 | 0.2552 | 0.5063 | 0.6485 | 0.8159 |


## Baseline (full-document prompt) coverage

- skipped: dataset has no page layout; the baseline's per-page cut cannot be reproduced

_Small or synthetic datasets only show whether the pipeline works, not whether one method is better._
