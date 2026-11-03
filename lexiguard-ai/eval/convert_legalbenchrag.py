"""
Converts LegalBench-RAG (Pipitone & Alami, 2024) into the harness dataset format.

Source layout (unzipped LegalBench-RAG.zip from the official repo's Dropbox link):
  <src>/corpus/<benchmark>/<file>.txt
  <src>/benchmarks/<benchmark>.json      {"tests": [{"query", "snippets": [{"file_path", "span": [s, e]}], "tags"}]}

Spans are character offsets into the corpus files. Files are copied byte-exact
so the offsets stay valid.

Differences from the official LegalBench-RAG setting (recorded in meta.json):
- Retrieval is within the gold document only (LexiGuard answers questions about
  one uploaded contract), not across the whole corpus. Scores are not comparable
  to the paper's.
- By default the "Consider the <document title>;" prefix that LegalBench-RAG adds
  to identify the document is removed, since the document is already known.
  Use --keep-doc-prefix to keep it.

Usage:
  python convert_legalbenchrag.py --src path\\to\\LegalBench-RAG --out data\\lbrag
  python convert_legalbenchrag.py --src ... --benchmarks contractnli,cuad --max-per-benchmark 100
"""

import argparse
import json
import random
import re
import shutil
from collections import defaultdict
from pathlib import Path

BENCHMARKS = ["contractnli", "cuad", "maud", "privacy_qa"]
_PREFIX_RE = re.compile(r"^\s*Consider\s+(?:the\s+)?.+?;\s*", re.IGNORECASE | re.DOTALL)


def read_exact(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def write_exact(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def flat_name(file_path: str) -> str:
    """corpus-relative path -> single file name, e.g. cuad/Foo Bar.txt -> cuad__Foo_Bar.txt"""
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", file_path.replace("/", "__").replace("\\", "__"))
    return stem if stem.endswith(".txt") else stem + ".txt"


def sample_tests(tests: list, max_tests: int, seed: str) -> list:
    """
    Deterministic sample that keeps the number of documents small: documents are
    shuffled with a fixed seed and taken whole until max_tests is reached
    (similar in spirit to the official benchmark's per-document sampling).
    """
    if max_tests <= 0 or len(tests) <= max_tests:
        return tests
    by_file = defaultdict(list)
    for t in tests:
        by_file[t["snippets"][0]["file_path"]].append(t)
    files = sorted(by_file)
    random.Random(seed).shuffle(files)
    out = []
    for f in files:
        if len(out) >= max_tests:
            break
        out.extend(by_file[f][: max_tests - len(out)])
    return out


class _Source:
    """Reads benchmark JSON and corpus files from the unzipped folder or straight from the zip.

    Reading from the zip avoids extraction problems: some corpus file names
    (e.g. MAUD files containing "||") are not valid on Windows.
    """

    def __init__(self, src: Path):
        self.zip = None
        self.prefix = ""
        if src.is_file() and src.suffix.lower() == ".zip":
            import zipfile
            self.zip = zipfile.ZipFile(src)
            names = [n.lstrip("/") for n in self.zip.namelist()]
            self._names = {n.lstrip("/"): n for n in self.zip.namelist()}
            # Allow a single top-level folder inside the zip
            hit = next((n for n in names if n.endswith("benchmarks/") or "/benchmarks/" in n or n.startswith("benchmarks/")), None)
            if hit is None:
                raise SystemExit(f"{src} has no benchmarks/ folder")
            self.prefix = hit[: hit.index("benchmarks/")]
        else:
            self.root = src
            if not (src / "corpus").is_dir() or not (src / "benchmarks").is_dir():
                raise SystemExit(f"Expected {src / 'corpus'} and {src / 'benchmarks'}. "
                                 "Point --src at LegalBench-RAG.zip or its unzipped folder.")

    def _read(self, rel: str) -> str:
        if self.zip is not None:
            key = self._names.get(self.prefix + rel)
            if key is None:
                raise FileNotFoundError(rel)
            return self.zip.read(key).decode("utf-8")   # bytes decode keeps offsets exact
        return read_exact(self.root / rel)

    def benchmark(self, name: str):
        try:
            return json.loads(self._read(f"benchmarks/{name}.json"))
        except FileNotFoundError:
            return None

    def corpus_text(self, file_path: str):
        try:
            return self._read(f"corpus/{file_path}")
        except FileNotFoundError:
            return None


def convert(src: Path, out: Path, benchmarks: list, max_per_benchmark: int, keep_prefix: bool, seed: str) -> dict:
    source = _Source(src)

    contracts_out = out / "contracts"
    if contracts_out.exists():
        shutil.rmtree(contracts_out)
    questions = []
    stats = {"skipped_multi_file": 0, "skipped_bad_span": 0, "skipped_missing_file": 0, "per_benchmark": {}}
    copied = {}

    for name in benchmarks:
        bench = source.benchmark(name)
        if bench is None:
            print(f"Skipping {name}: benchmarks/{name}.json not found")
            continue
        tests = bench["tests"]
        chosen = sample_tests(tests, max_per_benchmark, f"{seed}:{name}")
        kept = 0
        for i, t in enumerate(chosen):
            files = {s["file_path"] for s in t["snippets"]}
            if len(files) != 1:
                stats["skipped_multi_file"] += 1
                continue
            file_path = files.pop()
            if file_path not in copied:
                text = source.corpus_text(file_path)
                if text is None:
                    stats["skipped_missing_file"] += 1
                    continue
                write_exact(contracts_out / flat_name(file_path), text)
                copied[file_path] = text
            text = copied[file_path]
            gold = []
            ok = True
            for s in t["snippets"]:
                a, b = s["span"]
                if not (0 <= a < b <= len(text)):
                    ok = False
                    break
                gold.append({"text": text[a:b], "span": [a, b], "role": "primary"})
            if not ok:
                stats["skipped_bad_span"] += 1
                continue
            query = t["query"] if keep_prefix else _PREFIX_RE.sub("", t["query"], count=1)
            questions.append({
                "qid": f"lbrag-{name}-{i:04d}",
                "contract": flat_name(file_path),
                "type": name,
                "answerable": True,
                "question": query.strip(),
                "gold_evidence": gold,
                "gold_answer": "",
                "source_query": t["query"],
                "tags": t.get("tags", []),
            })
            kept += 1
        stats["per_benchmark"][name] = {"available": len(tests), "sampled": len(chosen), "kept": kept}

    out.mkdir(parents=True, exist_ok=True)
    with open(out / "questions.jsonl", "w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    meta = {
        "source": "LegalBench-RAG (Pipitone & Alami, 2024, arXiv:2408.10343)",
        "paginated": False,
        "setting_note": "within-document retrieval; not comparable to the paper's corpus-level scores",
        "doc_prefix_removed": not keep_prefix,
        "max_per_benchmark": max_per_benchmark,
        "seed": seed,
        "documents": len(copied),
        "questions": len(questions),
        **stats,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--src", required=True, help="unzipped LegalBench-RAG folder (contains corpus/ and benchmarks/)")
    p.add_argument("--out", default=str(Path(__file__).resolve().parent / "data" / "lbrag"))
    p.add_argument("--benchmarks", default=",".join(BENCHMARKS))
    p.add_argument("--max-per-benchmark", type=int, default=50, help="0 = all")
    p.add_argument("--keep-doc-prefix", action="store_true")
    p.add_argument("--seed", default="lexiguard")
    a = p.parse_args()
    meta = convert(Path(a.src), Path(a.out), [b.strip() for b in a.benchmarks.split(",") if b.strip()],
                   a.max_per_benchmark, a.keep_doc_prefix, a.seed)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
