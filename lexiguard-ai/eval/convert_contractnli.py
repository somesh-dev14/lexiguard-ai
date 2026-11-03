"""
Converts ContractNLI (Koreeda & Manning, 2021; CC BY 4.0) into the harness format.

Source: the unzipped contract-nli.zip from https://stanfordnlp.github.io/contract-nli/
  <src>/train.json, dev.json, test.json
  {"documents": [{"id", "file_name", "text", "spans": [[s, e], ...],
                  "annotation_sets": [{"annotations": {"nda-1": {"choice", "spans": [span indices]}}}]}],
   "labels": {"nda-1": {"short_description", "hypothesis"}}}

Every document is asked all 17 hypotheses. This is the part LegalBench-RAG
leaves out: hypotheses labelled NotMentioned become unanswerable questions,
so the harness can measure how the system handles information the contract
does not contain.

- Entailment     -> answerable, gold answer "Yes", gold evidence = annotated spans
- Contradiction  -> answerable, gold answer "No",  gold evidence = annotated spans
- NotMentioned   -> answerable = false, no gold evidence

Adjacent evidence spans (gap <= 1 char) are merged, as LegalBench-RAG does.

Usage:
  python convert_contractnli.py --src path\\to\\contract-nli --out data\\contractnli --split test --max-docs 30
"""

import argparse
import json
import random
import shutil
from pathlib import Path


def write_exact(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def merge_spans(spans, gap=1):
    out = []
    for s, e in sorted(spans):
        if out and s <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def question_for(hypothesis: str) -> str:
    return f"According to the agreement, is the following true: {hypothesis.strip().rstrip('.')}?"


def convert(src: Path, out: Path, split: str, max_docs: int, seed: str) -> dict:
    path = src / f"{split}.json"
    if not path.exists():
        raise SystemExit(f"{path} not found. Point --src at the unzipped contract-nli folder (it contains {split}.json).")
    data = json.loads(path.read_text(encoding="utf-8"))
    labels = data["labels"]
    docs = list(data["documents"])
    if max_docs and len(docs) > max_docs:
        docs = sorted(docs, key=lambda d: d["id"])
        random.Random(seed).shuffle(docs)
        docs = docs[:max_docs]

    contracts_out = out / "contracts"
    if contracts_out.exists():
        shutil.rmtree(contracts_out)
    questions = []
    counts = {"Entailment": 0, "Contradiction": 0, "NotMentioned": 0}

    for doc in docs:
        text = doc["text"]
        name = f"cnli_{doc['id']}.txt"
        write_exact(contracts_out / name, text)
        annotations = doc["annotation_sets"][0]["annotations"]
        for hid in sorted(labels, key=lambda h: int(h.split("-")[-1]) if h.split("-")[-1].isdigit() else h):
            ann = annotations.get(hid)
            if ann is None:
                continue
            choice = ann["choice"]
            counts[choice] = counts.get(choice, 0) + 1
            spans = merge_spans([doc["spans"][i] for i in ann.get("spans", [])])
            answerable = choice != "NotMentioned"
            questions.append({
                "qid": f"cnli-{doc['id']}-{hid}",
                "contract": name,
                "type": {"Entailment": "nli_entailment", "Contradiction": "nli_contradiction"}.get(choice, "absent"),
                "answerable": answerable,
                "question": question_for(labels[hid]["hypothesis"]),
                "gold_evidence": [{"text": text[s:e], "span": [s, e], "role": "primary"} for s, e in spans] if answerable else [],
                "gold_answer": {"Entailment": "Yes", "Contradiction": "No"}.get(choice, "Not addressed in the agreement."),
                "hypothesis_id": hid,
                "nli_label": choice,
            })

    out.mkdir(parents=True, exist_ok=True)
    with open(out / "questions.jsonl", "w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    meta = {
        "source": "ContractNLI (Koreeda & Manning, 2021), CC BY 4.0",
        "paginated": False,
        "split": split,
        "documents": len(docs),
        "questions": len(questions),
        "labels": counts,
        "max_docs": max_docs,
        "seed": seed,
        "question_template": question_for("<hypothesis>"),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--src", required=True, help="unzipped contract-nli folder (contains train/dev/test.json)")
    p.add_argument("--out", default=str(Path(__file__).resolve().parent / "data" / "contractnli"))
    p.add_argument("--split", default="test", choices=["train", "dev", "test"])
    p.add_argument("--max-docs", type=int, default=30, help="0 = all documents in the split")
    p.add_argument("--seed", default="lexiguard")
    a = p.parse_args()
    print(json.dumps(convert(Path(a.src), Path(a.out), a.split, a.max_docs, a.seed), indent=2))


if __name__ == "__main__":
    main()
