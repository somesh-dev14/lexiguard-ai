# Evidence retrieval evaluation harness

Experimental extension for the failure-aware evidence retrieval research.
It compares the original chat behaviour (full document in the prompt) with
**B1**, a plain one-shot clause retrieval baseline, and is the harness the
later evidence controller will be measured with.

## What it measures

**Part 1: retrieval (no LLM needed)**

For each retrieval variant (`bm25`, `dense`, `hybrid`, `hybrid+rerank`):

| Metric | Meaning |
|---|---|
| `hit@k` | at least one gold evidence text is in the top-k clauses |
| `complete@k` | **all** gold evidence texts are in the top-k clauses |
| `primary_recall@k` | share of primary gold items (the clause that directly answers) in the top-k |
| `dependency_recall@k` | share of dependency gold items (definition, cross-reference, override, attachment) in the top-k |
| `mrr` | 1 / rank of the first gold-bearing clause |

It also checks **baseline coverage**: whether each gold text is still present
in the prompt the original mode builds (pages are cut at 3,000 characters).
`--assumed-num-ctx N` additionally flags gold text whose position in that
prompt lies beyond an N-token window (rough chars/4 estimate).

**Part 2: chat pipeline (`--with-llm`, Ollama must be running)**

Runs the real `answer_document_question` in `baseline` and `retrieval` modes
and writes `grading.csv` for manual grading. Abstention and citation checks
in the summary are regex heuristics, not correctness judgments.

## Running

From `lexiguard-ai/backend` with the app venv:

```
venv\Scripts\python.exe ..\eval\run_eval.py
venv\Scripts\python.exe ..\eval\run_eval.py --with-llm
venv\Scripts\python.exe ..\eval\run_eval.py --data ..\eval\data\<set> --variants bm25,hybrid+rerank --ks 1,3,5
```

Results go to `eval/results/<timestamp>/`:
`config.json` (settings, index stats, model errors, dataset warnings),
`per_question.jsonl` (all raw data), `summary.json`, `summary.md`, and
`grading.csv` when `--with-llm` is used.

Dense retrieval and reranking use `sentence-transformers/all-MiniLM-L6-v2`
and `cross-encoder/ms-marco-MiniLM-L-6-v2` from the local Hugging Face cache
(offline). If they cannot load, the run says so in `config.json` and the
summary instead of silently falling back.

## External benchmarks

Two converters turn expert-annotated benchmarks into the harness format.
Downloads live outside the app, in `legal_ai_analyzer/eval_downloads/`.

| Benchmark | Download | What it adds |
|---|---|---|
| LegalBench-RAG (Pipitone & Alami 2024) | `LegalBench-RAG.zip`, 90.6 MB, Dropbox link in github.com/ZeroEntropy-AI/legalbenchrag | Character-span evidence over ContractNLI, CUAD, MAUD, PrivacyQA |
| ContractNLI (Koreeda & Manning 2021) | `contract-nli.zip`, 65.4 MB, stanfordnlp.github.io/contract-nli (CC BY 4.0, Hitachi America terms of use) | The `NotMentioned` label: expert-marked information the contract does **not** contain |

```
python -I convert_legalbenchrag.py --src ..\..\eval_downloads\LegalBench-RAG.zip --out data\lbrag --max-per-benchmark 50
python -I convert_contractnli.py --src ..\..\eval_downloads\cnli\contract-nli --out data\contractnli --split test --max-docs 30
cd ..\backend
venv\Scripts\python.exe ..\eval\run_eval.py --data ..\eval\data\lbrag --out ..\eval\results\lbrag
venv\Scripts\python.exe ..\eval\run_eval.py --data ..\eval\data\contractnli --out ..\eval\results\contractnli
```

The LegalBench-RAG converter reads the zip directly, because some corpus file
names (MAUD files containing `||`) cannot be extracted on Windows.

Important differences from the published benchmark setups:

- **Within-document retrieval.** Each question searches only its own contract,
  because LexiGuard answers questions about one uploaded document. LegalBench-RAG
  officially retrieves across the whole corpus, so the numbers are **not
  comparable to the paper**.
- The `Consider the <document>;` prefix in LegalBench-RAG queries is removed by
  default (`--keep-doc-prefix` keeps it).
- ContractNLI hypotheses become questions with the template
  `According to the agreement, is the following true: <hypothesis>?`.
- Sampling takes whole documents with a fixed seed, so a 50-question sample
  of one source may come from only a few documents.
- Converted data has no page layout, so the baseline page-cut check is skipped.

Converted contracts contain third-party text under the sources' licences:
keep `data/lbrag` and `data/contractnli` local, and attribute the sources in
anything you publish.

## Scoring by character span

Gold evidence is scored by character span. A gold span counts as retrieved at
rank k when the top-k clauses together cover at least `--span-threshold` of
its characters (default 50%). Spans split across clauses therefore count once
all their pieces are retrieved. `char_recall@k` and `char_precision@k` follow
LegalBench-RAG's character-level definitions. Hand-written datasets can give
gold evidence as text only; the harness finds the span itself.

## Dataset format

```
<set>/questions.jsonl
<set>/contracts/<name>.txt     pages separated by a line containing <<<PAGE>>>
<set>/contracts/<name>.pdf     extracted with the app's PDF extractor
```

One question per line:

```json
{"qid": "msa-09", "contract": "msa_synthetic.txt", "type": "definition",
 "answerable": true, "question": "How much must the Customer pay if it terminates for convenience?",
 "gold_evidence": [
   {"text": "subject to payment of the Early Termination Fee", "role": "primary"},
   {"text": "\"Early Termination Fee\" means an amount equal to ...", "role": "definition"}],
 "gold_answer": "The Early Termination Fee: the Charges for the three months before termination."}
```

- `gold_evidence[].text` must appear in the contract (whitespace and quote
  style are normalized). Optionally add `"span": [start, end]`, character
  offsets into the document text (pages joined with a newline); converted
  benchmarks always include it.
- `role`: `primary`, `definition`, `xref`, `override` or `attachment`.
- `answerable: false` with empty `gold_evidence` marks information the
  contract does not contain.

The run validates every gold item, warns if it is missing from the contract,
and counts gold spans that cross a clause boundary. An optional `meta.json`
holds the source and `"paginated": false` for text without page layout.

## The seed set is not a benchmark

`data/seed/` has 2 contracts and 25 questions. `msa_synthetic.txt` was written
for this harness, and its questions were written knowing what the evidence
controller is meant to fix. Use it to check that the pipeline works, never as
evidence that one method is better. Real conclusions need:

- external data with expert evidence annotations (LegalBench-RAG spans over
  CUAD / MAUD / ContractNLI; ContractNLI `NotMentioned` for absent information)
- a dependency-question set written on real contracts by someone who has not
  seen the system's outputs
- counterfactual deletions (remove the gold clause to create "absent" cases)
