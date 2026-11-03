# B1 baseline on expert-annotated data (2026-10-25)

Runs: `results/lbrag/20261025-131412` and `results/contractnli/20261025-131836`.
Raw data is in each run's `per_question.jsonl`; settings in `config.json`.

## Setup

- **B1** = one-shot clause retrieval from the upload-time evidence index
  (BM25, MiniLM dense, RRF fusion, ms-marco MiniLM cross-encoder).
- **Within-document retrieval**: each question searches only its own contract.
  Not comparable to LegalBench-RAG's published corpus-level numbers.
- A gold span counts as retrieved when the top-k clauses cover at least 50% of it.
- LegalBench-RAG sample: 200 questions over 18 documents (50 per source,
  whole-document sampling, seed "lexiguard"). ContractNLI: test split,
  30 documents x 17 hypotheses = 510 questions (291 answerable, 219 NotMentioned).

## Results at k = 5 (the app's default top-k)

| | complete@5 bm25 | complete@5 hybrid | complete@5 hybrid+rerank | char_precision@5 (rerank) |
|---|---|---|---|---|
| LegalBench-RAG, all (n=200) | 0.795 | 0.805 | 0.810 | 0.064 |
| - ContractNLI subset (50) | 0.94 | 0.92 | 0.94 | |
| - CUAD (50) | 0.80 | 0.84 | 0.96 | |
| - MAUD (50) | 0.46 | 0.46 | 0.34 | |
| - PrivacyQA (50) | 0.98 | 1.00 | 1.00 | |
| ContractNLI answerable (n=291) | 0.894 | 0.887 | 0.866 | 0.070 |

## What this shows

1. **One-shot retrieval leaves a measurable gap.** At the app's top-5, about
   1 in 5 LegalBench-RAG questions and 1 in 8 ContractNLI questions lack their
   full gold evidence. Those questions are the population an evidence controller
   would have to fix.
2. **The general-web reranker does not help on contracts.** On ContractNLI it is
   below BM25 alone at every k; on MAUD it is worse than no reranker. A
   legal-domain or fine-tuned reranker would be needed before reranking earns its cost.
3. **Segmentation is the first bottleneck on long agreements.** The analysis
   chunker turned one 313k-character MAUD agreement into 2 clauses and a
   504k-character one into 29. The embedding model reads ~256 tokens and the
   reranker ~512 per clause, so most of such a clause is invisible to them.
4. **Some scores are inflated by oversized clauses.** All 30 PrivacyQA gold
   spans sit inside clauses longer than 8,000 characters, so one huge clause
   "covers" the answer (character precision at k=5 is about 0.06). Hit/complete
   numbers must always be read together with char_precision.
5. **MAUD is hard independently of clause size**: gold evidence inside small
   clauses (< 2k chars) was missed 9/9 times at k=5.
6. **Retrieval scores barely signal missing information.** On ContractNLI, the
   top-1 score separates answerable from NotMentioned questions with AUROC
   0.60 (BM25), 0.66 (dense), 0.67 (cross-encoder); 0.5 is chance. A score
   threshold cannot decide when to abstain, which supports a per-requirement
   evidence check instead.

## Caveats

- Small samples from few documents (MAUD's 50 questions come from 4 agreements).
  Differences of a few points between variants are within noise; no significance
  tests were run.
- ContractNLI questions all use one template built from the hypotheses.
- The chat (LLM) stage was not run on these sets; only retrieval was measured.

## Suggested next steps before the controller

1. Cap clause size in the evidence index (split oversized clauses by paragraph /
   sentence windows) and re-measure B1, so later gains are not just a segmentation fix.
2. Make B1's default BM25 + dense without the ms-marco reranker, or evaluate a
   legal-domain reranker.
3. Then build the controller and compare it with this B1 on the same data.
