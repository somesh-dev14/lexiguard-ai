# Evaluation run

- Started: 2026-10-25T13:54:49
- Data: `C:\Users\warso\Downloads\legal_ai_analyzer\lexiguard-ai\eval\data\contractnli` (510 questions)
- Source: ContractNLI (Koreeda & Manning, 2021), CC BY 4.0
- Setting: within-document retrieval: each question searches only the clauses of its own contract
- A gold span counts as retrieved when the top-k clauses cover >= 50% of it
- Dataset warnings: 0; gold spans crossing clause boundaries: 14
- Model load errors: none

## Retrieval (answerable questions)

| variant | n | mrr | hit@1 | hit@3 | hit@5 | hit@10 | complete@1 | complete@3 | complete@5 | complete@10 | char_recall@1 | char_recall@3 | char_recall@5 | char_recall@10 | char_precision@1 | char_precision@3 | char_precision@5 | char_precision@10 | primary_recall@1 | primary_recall@3 | primary_recall@5 | primary_recall@10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 291 | 0.7631 | 0.6426 | 0.8625 | 0.9278 | 0.9897 | 0.4914 | 0.7698 | 0.8591 | 0.9691 | 0.5766 | 0.821 | 0.9029 | 0.9784 | 0.2033 | 0.102 | 0.0753 | 0.0557 | 0.5293 | 0.795 | 0.8806 | 0.9707 |
| hybrid | 291 | 0.7395 | 0.5911 | 0.8591 | 0.9416 | 0.9897 | 0.4639 | 0.756 | 0.8969 | 0.9656 | 0.5357 | 0.8146 | 0.9223 | 0.979 | 0.1895 | 0.1041 | 0.0798 | 0.055 | 0.4977 | 0.786 | 0.9099 | 0.9707 |

### complete@k by question type

| variant | type | n | complete@1 | complete@3 | complete@5 | complete@10 |
|---|---|---|---|---|---|---|
| bm25 | nli_contradiction | 52 | 0.5385 | 0.7692 | 0.8654 | 1.0 |
| bm25 | nli_entailment | 239 | 0.4812 | 0.7699 | 0.8577 | 0.9623 |
| hybrid | nli_contradiction | 52 | 0.5 | 0.7115 | 0.8846 | 1.0 |
| hybrid | nli_entailment | 239 | 0.4561 | 0.7657 | 0.8996 | 0.9582 |


## Baseline (full-document prompt) coverage

- skipped: dataset has no page layout; the baseline's per-page cut cannot be reproduced

_Small or synthetic datasets only show whether the pipeline works, not whether one method is better._
