# Evaluation run

- Started: 2026-10-24T22:16:06
- Data: `C:\Users\warso\Downloads\legal_ai_analyzer\lexiguard-ai\eval\data\seed` (25 questions)
- Source: local
- Setting: within-document retrieval: each question searches only the clauses of its own contract
- A gold span counts as retrieved when the top-k clauses cover >= 50% of it
- Dataset warnings: 0; gold spans crossing clause boundaries: 0
- Model load errors: none

## Retrieval (answerable questions)

| variant | n | mrr | hit@1 | hit@3 | hit@5 | hit@10 | complete@1 | complete@3 | complete@5 | complete@10 | char_recall@1 | char_recall@3 | char_recall@5 | char_recall@10 | char_precision@1 | char_precision@3 | char_precision@5 | char_precision@10 | primary_recall@1 | primary_recall@3 | primary_recall@5 | primary_recall@10 | dependency_recall@1 | dependency_recall@3 | dependency_recall@5 | dependency_recall@10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 20 | 0.9667 | 0.95 | 1.0 | 1.0 | 1.0 | 0.7 | 0.8 | 0.8 | 0.9 | 0.8361 | 0.9015 | 0.9015 | 0.9449 | 0.3224 | 0.1393 | 0.089 | 0.0573 | 0.8 | 0.9 | 0.9 | 1.0 | 0.6667 | 0.6667 | 0.6667 | 0.6667 |
| hybrid+rerank | 20 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.75 | 0.85 | 0.85 | 0.9 | 0.8861 | 0.9214 | 0.9214 | 0.9449 | 0.3389 | 0.1198 | 0.0748 | 0.0393 | 0.85 | 0.95 | 0.95 | 1.0 | 0.6667 | 0.6667 | 0.6667 | 0.6667 |

### complete@k by question type

| variant | type | n | complete@1 | complete@3 | complete@5 | complete@10 |
|---|---|---|---|---|---|---|
| bm25 | attachment | 2 | 0.5 | 0.5 | 0.5 | 1.0 |
| bm25 | definition | 1 | 0.0 | 0.0 | 0.0 | 0.0 |
| bm25 | direct | 14 | 0.9286 | 1.0 | 1.0 | 1.0 |
| bm25 | override | 2 | 0.0 | 0.5 | 0.5 | 1.0 |
| bm25 | xref | 1 | 0.0 | 0.0 | 0.0 | 0.0 |
| hybrid+rerank | attachment | 2 | 0.5 | 1.0 | 1.0 | 1.0 |
| hybrid+rerank | definition | 1 | 0.0 | 0.0 | 0.0 | 0.0 |
| hybrid+rerank | direct | 14 | 1.0 | 1.0 | 1.0 | 1.0 |
| hybrid+rerank | override | 2 | 0.0 | 0.5 | 0.5 | 1.0 |
| hybrid+rerank | xref | 1 | 0.0 | 0.0 | 0.0 | 0.0 |


## Baseline (full-document prompt) coverage

- gold_items_present: 25/26
- questions_with_all_gold_present: 19/20
- est_prompt_tokens_by_contract: {'msa_synthetic.txt': 2642, 'sample_service_agreement.txt': 407}

_Small or synthetic datasets only show whether the pipeline works, not whether one method is better._
