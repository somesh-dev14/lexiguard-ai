# Evaluation run

- Started: 2026-10-24T20:57:07
- Data: `C:\Users\warso\Downloads\legal_ai_analyzer\lexiguard-ai\eval\data\seed` (25 questions)
- Dataset warnings: 0
- Model load errors: none

## Retrieval (answerable questions)

| variant | n | mrr | hit@1 | hit@3 | hit@5 | hit@10 | complete@1 | complete@3 | complete@5 | complete@10 | primary_recall@1 | primary_recall@3 | primary_recall@5 | primary_recall@10 | dependency_recall@1 | dependency_recall@3 | dependency_recall@5 | dependency_recall@10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 20 | 0.9667 | 0.95 | 1.0 | 1.0 | 1.0 | 0.7 | 0.8 | 0.8 | 0.9 | 0.8 | 0.9 | 0.9 | 1.0 | 0.6667 | 0.6667 | 0.6667 | 0.6667 |
| hybrid+rerank | 20 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.75 | 0.85 | 0.85 | 0.9 | 0.85 | 0.95 | 0.95 | 1.0 | 0.6667 | 0.6667 | 0.6667 | 0.6667 |


## Baseline (full-document prompt) coverage

- gold_items_present: 25/26
- questions_with_all_gold_present: 19/20
- est_prompt_tokens_by_contract: {'msa_synthetic.txt': 2642, 'sample_service_agreement.txt': 407}

## Chat pipeline (heuristic checks; grade grading.csv by hand)

- **baseline**: {'n': 25, 'errors': 0, 'mean_seconds': 9.18, 'answerable_abstained_heuristic': '1/20', 'unanswerable_abstained_heuristic': '3/5', 'answerable_citation_hits_gold': '19/20', 'note': 'Abstention and citation checks are heuristics; grade correctness in grading.csv.'}
- **retrieval**: {'n': 25, 'errors': 0, 'mean_seconds': 7.31, 'answerable_abstained_heuristic': '0/20', 'unanswerable_abstained_heuristic': '5/5', 'answerable_citation_hits_gold': '20/20', 'note': 'Abstention and citation checks are heuristics; grade correctness in grading.csv.'}

_Small or synthetic datasets only show whether the pipeline works, not whether one method is better._
