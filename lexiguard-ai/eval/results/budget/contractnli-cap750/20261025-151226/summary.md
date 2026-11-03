# Evaluation run

- Started: 2026-10-25T15:12:26
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

### Equal text budget (what fits in the prompt)

| variant | budget4000_char_precision | budget4000_char_recall | budget4000_chars | budget4000_clauses | budget4000_complete | budget8000_char_precision | budget8000_char_recall | budget8000_chars | budget8000_clauses | budget8000_complete | budget12000_char_precision | budget12000_char_recall | budget12000_chars | budget12000_clauses | budget12000_complete |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 0.1025 | 0.7559 | 3278.4 | 7.0 | 0.6529 | 0.0698 | 0.9128 | 6264.1 | 13.3 | 0.8832 | 0.0559 | 0.9545 | 8513.7 | 18.6 | 0.945 |
| hybrid | 0.1072 | 0.8037 | 3307.3 | 7.3 | 0.7182 | 0.07 | 0.9348 | 6345.2 | 14.1 | 0.8969 | 0.0556 | 0.9697 | 8676.8 | 19.6 | 0.9622 |

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
