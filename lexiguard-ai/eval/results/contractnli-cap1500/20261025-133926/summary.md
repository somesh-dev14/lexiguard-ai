# Evaluation run

- Started: 2026-10-25T13:39:26
- Data: `C:\Users\warso\Downloads\legal_ai_analyzer\lexiguard-ai\eval\data\contractnli` (510 questions)
- Source: ContractNLI (Koreeda & Manning, 2021), CC BY 4.0
- Setting: within-document retrieval: each question searches only the clauses of its own contract
- A gold span counts as retrieved when the top-k clauses cover >= 50% of it
- Dataset warnings: 0; gold spans crossing clause boundaries: 33
- Model load errors: none

## Retrieval (answerable questions)

| variant | n | mrr | hit@1 | hit@3 | hit@5 | hit@10 | complete@1 | complete@3 | complete@5 | complete@10 | char_recall@1 | char_recall@3 | char_recall@5 | char_recall@10 | char_precision@1 | char_precision@3 | char_precision@5 | char_precision@10 | primary_recall@1 | primary_recall@3 | primary_recall@5 | primary_recall@10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 291 | 0.6736 | 0.5361 | 0.7595 | 0.8591 | 0.9725 | 0.3711 | 0.6289 | 0.7595 | 0.9244 | 0.4743 | 0.6964 | 0.8118 | 0.9496 | 0.2391 | 0.1218 | 0.0915 | 0.0635 | 0.4144 | 0.6712 | 0.7905 | 0.9347 |
| dense | 291 | 0.609 | 0.4399 | 0.7354 | 0.866 | 0.9622 | 0.3299 | 0.5842 | 0.7388 | 0.8866 | 0.3843 | 0.6561 | 0.8051 | 0.9266 | 0.2047 | 0.1327 | 0.1007 | 0.0642 | 0.3446 | 0.6396 | 0.7725 | 0.9077 |
| hybrid | 291 | 0.679 | 0.5292 | 0.7869 | 0.8969 | 0.9828 | 0.3883 | 0.6495 | 0.7938 | 0.9416 | 0.4642 | 0.7225 | 0.8517 | 0.9626 | 0.2364 | 0.1331 | 0.0991 | 0.0638 | 0.4189 | 0.6982 | 0.8243 | 0.9505 |
| hybrid+rerank | 291 | 0.6561 | 0.5017 | 0.7595 | 0.8729 | 0.9622 | 0.3471 | 0.6426 | 0.7629 | 0.9313 | 0.4306 | 0.6991 | 0.8139 | 0.9501 | 0.2248 | 0.1258 | 0.0965 | 0.0642 | 0.3829 | 0.6667 | 0.786 | 0.9369 |

### complete@k by question type

| variant | type | n | complete@1 | complete@3 | complete@5 | complete@10 |
|---|---|---|---|---|---|---|
| bm25 | nli_contradiction | 52 | 0.3846 | 0.6346 | 0.7692 | 0.9615 |
| bm25 | nli_entailment | 239 | 0.3682 | 0.6276 | 0.7573 | 0.9163 |
| dense | nli_contradiction | 52 | 0.3654 | 0.6346 | 0.7692 | 0.9615 |
| dense | nli_entailment | 239 | 0.3222 | 0.5732 | 0.7322 | 0.8703 |
| hybrid | nli_contradiction | 52 | 0.4231 | 0.6346 | 0.7885 | 0.9615 |
| hybrid | nli_entailment | 239 | 0.3808 | 0.6527 | 0.795 | 0.9372 |
| hybrid+rerank | nli_contradiction | 52 | 0.3846 | 0.6538 | 0.75 | 0.9615 |
| hybrid+rerank | nli_entailment | 239 | 0.3389 | 0.6402 | 0.7657 | 0.9247 |


## Baseline (full-document prompt) coverage

- skipped: dataset has no page layout; the baseline's per-page cut cannot be reproduced

_Small or synthetic datasets only show whether the pipeline works, not whether one method is better._
