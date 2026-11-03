# Evaluation run

- Started: 2026-10-25T14:54:12
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
| hybrid+rerank | 291 | 0.7053 | 0.5464 | 0.8316 | 0.9244 | 0.9794 | 0.4192 | 0.7354 | 0.8557 | 0.9656 | 0.4885 | 0.7884 | 0.8973 | 0.9741 | 0.1819 | 0.1022 | 0.0797 | 0.0558 | 0.4617 | 0.7658 | 0.8806 | 0.964 |

### Equal text budget (what fits in the prompt)

| variant | budget4000_char_precision | budget4000_char_recall | budget4000_chars | budget4000_clauses | budget4000_complete | budget8000_char_precision | budget8000_char_recall | budget8000_chars | budget8000_clauses | budget8000_complete | budget12000_char_precision | budget12000_char_recall | budget12000_chars | budget12000_clauses | budget12000_complete |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 0.0985 | 0.7301 | 3298.5 | 3.6 | 0.6701 | 0.0668 | 0.9049 | 6608.5 | 6.7 | 0.8729 | 0.0547 | 0.9698 | 9030.6 | 9.4 | 0.9588 |
| hybrid | 0.1003 | 0.7107 | 3276.8 | 4.0 | 0.646 | 0.0682 | 0.9258 | 6626.9 | 7.2 | 0.8866 | 0.0547 | 0.9824 | 9058.8 | 9.9 | 0.9725 |
| hybrid+rerank | 0.0938 | 0.6669 | 3240.9 | 4.0 | 0.6151 | 0.0658 | 0.8947 | 6606.8 | 7.2 | 0.8557 | 0.0545 | 0.9783 | 9044.0 | 10.0 | 0.9622 |

### complete@k by question type

| variant | type | n | complete@1 | complete@3 | complete@5 | complete@10 |
|---|---|---|---|---|---|---|
| bm25 | nli_contradiction | 52 | 0.5385 | 0.7692 | 0.8654 | 1.0 |
| bm25 | nli_entailment | 239 | 0.4812 | 0.7699 | 0.8577 | 0.9623 |
| hybrid | nli_contradiction | 52 | 0.5 | 0.7115 | 0.8846 | 1.0 |
| hybrid | nli_entailment | 239 | 0.4561 | 0.7657 | 0.8996 | 0.9582 |
| hybrid+rerank | nli_contradiction | 52 | 0.3462 | 0.7308 | 0.8269 | 1.0 |
| hybrid+rerank | nli_entailment | 239 | 0.4351 | 0.7364 | 0.8619 | 0.9582 |


## Baseline (full-document prompt) coverage

- skipped: dataset has no page layout; the baseline's per-page cut cannot be reproduced

_Small or synthetic datasets only show whether the pipeline works, not whether one method is better._
