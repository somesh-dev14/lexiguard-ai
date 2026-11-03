# Evaluation run

- Started: 2026-10-25T13:18:36
- Data: `C:\Users\warso\Downloads\legal_ai_analyzer\lexiguard-ai\eval\data\contractnli` (510 questions)
- Source: ContractNLI (Koreeda & Manning, 2021), CC BY 4.0
- Setting: within-document retrieval: each question searches only the clauses of its own contract
- A gold span counts as retrieved when the top-k clauses cover >= 50% of it
- Dataset warnings: 0; gold spans crossing clause boundaries: 5
- Model load errors: none

## Retrieval (answerable questions)

| variant | n | mrr | hit@1 | hit@3 | hit@5 | hit@10 | complete@1 | complete@3 | complete@5 | complete@10 | char_recall@1 | char_recall@3 | char_recall@5 | char_recall@10 | char_precision@1 | char_precision@3 | char_precision@5 | char_precision@10 | primary_recall@1 | primary_recall@3 | primary_recall@5 | primary_recall@10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 291 | 0.8287 | 0.7457 | 0.9003 | 0.945 | 0.9897 | 0.622 | 0.8179 | 0.8935 | 0.9691 | 0.6959 | 0.8658 | 0.9245 | 0.9785 | 0.1747 | 0.0888 | 0.068 | 0.0546 | 0.6509 | 0.8401 | 0.9032 | 0.9707 |
| dense | 291 | 0.6645 | 0.5223 | 0.7766 | 0.8832 | 0.9519 | 0.4364 | 0.6735 | 0.8385 | 0.9313 | 0.4775 | 0.7257 | 0.8628 | 0.9382 | 0.1368 | 0.092 | 0.0729 | 0.052 | 0.4505 | 0.6982 | 0.8468 | 0.9392 |
| hybrid | 291 | 0.7819 | 0.677 | 0.8522 | 0.921 | 0.9931 | 0.5808 | 0.7835 | 0.8866 | 0.9725 | 0.6342 | 0.8205 | 0.9026 | 0.9829 | 0.1589 | 0.0883 | 0.0687 | 0.0538 | 0.5991 | 0.8108 | 0.8896 | 0.9752 |
| hybrid+rerank | 291 | 0.7532 | 0.6357 | 0.8316 | 0.9038 | 0.9794 | 0.5464 | 0.7663 | 0.866 | 0.9691 | 0.5973 | 0.8035 | 0.8865 | 0.9746 | 0.1633 | 0.0905 | 0.0699 | 0.0547 | 0.5631 | 0.7928 | 0.8851 | 0.9662 |

### complete@k by question type

| variant | type | n | complete@1 | complete@3 | complete@5 | complete@10 |
|---|---|---|---|---|---|---|
| bm25 | nli_contradiction | 52 | 0.6538 | 0.8077 | 0.9231 | 1.0 |
| bm25 | nli_entailment | 239 | 0.6151 | 0.8201 | 0.887 | 0.9623 |
| dense | nli_contradiction | 52 | 0.4615 | 0.7308 | 0.8654 | 0.9423 |
| dense | nli_entailment | 239 | 0.431 | 0.6611 | 0.8326 | 0.9289 |
| hybrid | nli_contradiction | 52 | 0.6154 | 0.75 | 0.9038 | 1.0 |
| hybrid | nli_entailment | 239 | 0.5732 | 0.7908 | 0.8828 | 0.9665 |
| hybrid+rerank | nli_contradiction | 52 | 0.5577 | 0.7692 | 0.8654 | 1.0 |
| hybrid+rerank | nli_entailment | 239 | 0.5439 | 0.7657 | 0.8661 | 0.9623 |


## Baseline (full-document prompt) coverage

- skipped: dataset has no page layout; the baseline's per-page cut cannot be reproduced

_Small or synthetic datasets only show whether the pipeline works, not whether one method is better._
