"""
Tests for the benchmark converters and span-based metrics.

Fixtures are tiny hand-made files in the LegalBench-RAG and ContractNLI
formats; no real benchmark data is needed. Runs with BM25 only (no torch).

Run from lexiguard-ai/backend:
  venv\\Scripts\\python.exe -m pytest ..\\eval\\tests -q
"""

import json
import subprocess
import sys
from pathlib import Path

import convert_contractnli
import convert_legalbenchrag
import dataset as ds
import metrics as m

EVAL_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = EVAL_DIR.parent / "backend"

NDA_TEXT = (
    "MUTUAL NON-DISCLOSURE AGREEMENT\r\n\r\n"
    "1. Confidential Information. \"Confidential Information\" means all non-public information disclosed by a party.\r\n\r\n"
    "2. Obligations. The Receiving Party shall not disclose Confidential Information to any third party.\r\n"
    "The Receiving Party may share Confidential Information with its employees who need to know it.\r\n\r\n"
    "3. Term. This Agreement remains in force for three (3) years from the Effective Date.\r\n\r\n"
    "4. Return of Information. On request, the Receiving Party shall return or destroy all Confidential Information.\r\n"
)


def _span(text, phrase):
    i = text.index(phrase)
    return [i, i + len(phrase)]


# ---------------------------------------------------------------------------
# Span metrics
# ---------------------------------------------------------------------------

def test_gold_ranks_requires_coverage_threshold():
    gold = [(100, 200)]
    ranked = [(0, 120), (120, 300)]          # first clause covers 20%, both cover 100%
    assert m.gold_ranks(gold, ranked, 0.5) == [2]
    assert m.gold_ranks(gold, ranked, 0.2) == [1]
    assert m.gold_ranks(gold, [(500, 600)], 0.5) == [None]
    assert m.gold_ranks([None], ranked, 0.5) == [None]


def test_char_precision_recall():
    gold = [(0, 100)]
    ranked = [(50, 150), (0, 50)]
    top1 = m.char_precision_recall(gold, ranked, 1)
    assert top1 == {"char_recall": 0.5, "char_precision": 0.5}
    top2 = m.char_precision_recall(gold, ranked, 2)
    assert top2["char_recall"] == 1.0 and abs(top2["char_precision"] - 100 / 150) < 1e-9


def test_fill_budget_skips_and_truncates_like_a_prompt():
    # second clause does not fit, third does (skip-and-continue like format_context)
    assert m.fill_budget([400, 900, 300], 1000, separator=0) == [(0, 400), (2, 300)]
    # a single giant first clause only counts up to the budget
    assert m.fill_budget([300000, 100], 12000, separator=0) == [(0, 12000)]


def test_find_span_ignores_whitespace_and_quotes():
    full = 'Payment is due\n  within “thirty” days.'
    assert ds.find_span(full, 'due within "thirty" days') == (11, len(full) - 1)


# ---------------------------------------------------------------------------
# Converters
# ---------------------------------------------------------------------------

def _make_lbrag(root: Path) -> Path:
    src = root / "LegalBench-RAG"
    (src / "corpus" / "contractnli").mkdir(parents=True)
    (src / "benchmarks").mkdir(parents=True)
    with open(src / "corpus" / "contractnli" / "Sample NDA.txt", "w", encoding="utf-8", newline="") as f:
        f.write(NDA_TEXT)
    tests = {"tests": [
        {"query": "Consider the Mutual Non-Disclosure Agreement; Does the agreement allow sharing with employees?",
         "snippets": [{"file_path": "contractnli/Sample NDA.txt",
                       "span": _span(NDA_TEXT, "The Receiving Party may share Confidential Information with its employees who need to know it.")}]},
        {"query": "Consider the Mutual Non-Disclosure Agreement; How long does the agreement last?",
         "snippets": [{"file_path": "contractnli/Sample NDA.txt",
                       "span": _span(NDA_TEXT, "This Agreement remains in force for three (3) years from the Effective Date.")}]},
    ]}
    (src / "benchmarks" / "contractnli.json").write_text(json.dumps(tests), encoding="utf-8")
    return src


def _make_cnli(root: Path) -> Path:
    src = root / "contract-nli"
    src.mkdir(parents=True)
    spans = [
        _span(NDA_TEXT, "The Receiving Party shall not disclose Confidential Information to any third party."),
        _span(NDA_TEXT, "The Receiving Party may share Confidential Information with its employees who need to know it."),
        _span(NDA_TEXT, "On request, the Receiving Party shall return or destroy all Confidential Information."),
    ]
    data = {
        "documents": [{
            "id": 7, "file_name": "nda.pdf", "text": NDA_TEXT, "spans": spans,
            "annotation_sets": [{"annotations": {
                "nda-1": {"choice": "Entailment", "spans": [1]},
                "nda-2": {"choice": "Contradiction", "spans": [0]},
                "nda-3": {"choice": "NotMentioned", "spans": []},
            }}],
        }],
        "labels": {
            "nda-1": {"short_description": "Sharing with employees", "hypothesis": "Receiving Party may share some Confidential Information with some of Receiving Party's employees."},
            "nda-2": {"short_description": "Sharing with third-parties", "hypothesis": "Receiving Party may share some Confidential Information with some third-parties."},
            "nda-3": {"short_description": "Survival of obligations", "hypothesis": "Some obligations of Agreement may survive termination of Agreement."},
        },
    }
    (src / "test.json").write_text(json.dumps(data), encoding="utf-8")
    return src


def test_legalbenchrag_converter_keeps_offsets_exact(tmp_path):
    out = tmp_path / "lbrag"
    meta = convert_legalbenchrag.convert(_make_lbrag(tmp_path), out, ["contractnli"], 50, False, "s")
    assert meta["questions"] == 2 and meta["paginated"] is False

    qs = ds.load_questions(out / "questions.jsonl")
    assert qs[0].question == "Does the agreement allow sharing with employees?"   # doc prefix removed
    doc = ds.load_contract(out / "contracts" / qs[0].contract)
    assert ds.resolve_spans(qs, {qs[0].contract: doc}) == []
    full = doc.pages[0].text
    assert "\r\n" in full                                                          # byte-exact copy
    s, e = qs[0].gold_evidence[0].span
    assert full[s:e].startswith("The Receiving Party may share")


def test_legalbenchrag_converter_reads_zip(tmp_path):
    import zipfile
    src = _make_lbrag(tmp_path)
    zpath = tmp_path / "LegalBench-RAG.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for f in src.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(src).as_posix())
    meta = convert_legalbenchrag.convert(zpath, tmp_path / "out", ["contractnli"], 50, False, "s")
    assert meta["questions"] == 2 and meta["skipped_missing_file"] == 0


def test_contractnli_converter_marks_notmentioned_unanswerable(tmp_path):
    out = tmp_path / "cnli"
    meta = convert_contractnli.convert(_make_cnli(tmp_path), out, "test", 0, "s")
    assert meta["labels"] == {"Entailment": 1, "Contradiction": 1, "NotMentioned": 1}

    qs = {q.qid: q for q in ds.load_questions(out / "questions.jsonl")}
    assert qs["cnli-7-nda-1"].answerable and qs["cnli-7-nda-1"].gold_answer == "Yes"
    assert qs["cnli-7-nda-2"].type == "nli_contradiction"
    assert not qs["cnli-7-nda-3"].answerable and qs["cnli-7-nda-3"].gold_evidence == []


def test_index_char_offsets_line_up_with_document_text():
    from app.services.evidence.index import build_evidence_index, document_text
    from app.schemas.document import DocumentDetail, PageText
    doc = DocumentDetail(id="t", filename="t.txt", page_count=1, word_count=1, uploadedAt="", status="ready",
                         pages=[PageText(page_number=1, text=NDA_TEXT)])
    ix = build_evidence_index(doc)
    full = document_text(doc)
    for c in ix.clauses:
        assert c.char_start is not None
        assert " ".join(full[c.char_start:c.char_end].split()) == " ".join(c.text.split())
    assert ix.build_info["char_coverage"] > 0.9


# ---------------------------------------------------------------------------
# End to end: converter -> run_eval (BM25 only)
# ---------------------------------------------------------------------------

def _run_eval(data_dir: Path, out_dir: Path):
    python = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
    exe = str(python) if python.exists() else sys.executable
    proc = subprocess.run(
        [exe, str(EVAL_DIR / "run_eval.py"), "--data", str(data_dir), "--out", str(out_dir),
         "--variants", "bm25", "--ks", "1,3"],
        capture_output=True, text=True, timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    run = next(out_dir.iterdir())
    return json.loads((run / "summary.json").read_text()), json.loads((run / "config.json").read_text())


def test_end_to_end_contractnli(tmp_path):
    data = tmp_path / "cnli"
    convert_contractnli.convert(_make_cnli(tmp_path), data, "test", 0, "s")
    summary, config = _run_eval(data, tmp_path / "results")
    assert config["dataset_warnings"] == []
    s = summary["retrieval"]["bm25"]
    assert s["n"] == 2                         # NotMentioned question excluded from retrieval metrics
    assert "char_recall@3" in s and "hit@1" in s
    assert "skipped" in summary["baseline_context"]


def test_end_to_end_legalbenchrag(tmp_path):
    data = tmp_path / "lbrag"
    convert_legalbenchrag.convert(_make_lbrag(tmp_path), data, ["contractnli"], 50, False, "s")
    summary, _ = _run_eval(data, tmp_path / "results")
    assert summary["retrieval"]["bm25"]["n"] == 2
