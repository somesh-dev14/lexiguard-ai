"""
Evaluation dataset loading and validation.

Dataset layout:
  <data_dir>/questions.jsonl
  <data_dir>/meta.json              optional: {"source": ..., "paginated": true|false, ...}
  <data_dir>/contracts/<file>.txt   pages separated by a line "<<<PAGE>>>"
  <data_dir>/contracts/<file>.pdf   extracted with the app's own PDF extractor

Each question line:
  {"qid", "contract", "type", "answerable", "question",
   "gold_evidence": [{"text": ..., "span": [start, end] (optional), "role": ...}],
   "gold_answer": reference answer for human grading}

Gold evidence is scored by character span in the document text (pages joined
by "\\n", exactly as the app's chunker joins them). Items given only as text
get their span by searching the document, so hand-written datasets need no
offsets and segmentation changes never invalidate a dataset.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PAGE_BREAK = "<<<PAGE>>>"


def norm(text: str) -> str:
    text = (text or "").replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    return " ".join(text.lower().split())


@dataclass
class GoldItem:
    text: str
    role: str = "primary"
    span: Optional[Tuple[int, int]] = None


@dataclass
class Question:
    qid: str
    contract: str
    type: str
    answerable: bool
    question: str
    gold_evidence: List[GoldItem] = field(default_factory=list)
    gold_answer: str = ""


def load_meta(data_dir: Path) -> dict:
    path = data_dir / "meta.json"
    meta = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    meta.setdefault("paginated", True)
    return meta


def load_questions(path: Path) -> List[Question]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        out.append(Question(
            qid=row["qid"],
            contract=row["contract"],
            type=row.get("type", "unspecified"),
            answerable=bool(row.get("answerable", True)),
            question=row["question"],
            gold_evidence=[
                GoldItem(g.get("text", ""), g.get("role", "primary"), tuple(g["span"]) if g.get("span") else None)
                for g in row.get("gold_evidence", [])
            ],
            gold_answer=row.get("gold_answer", ""),
        ))
    return out


def read_text_exact(path: Path) -> str:
    """Reads text without newline translation, so character offsets stay exact."""
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def load_contract(path: Path, doc_id: Optional[str] = None):
    """Returns an app DocumentDetail for a .txt or .pdf contract."""
    from app.schemas.document import DocumentDetail, PageText

    if path.suffix.lower() == ".pdf":
        from app.services.pdf_extractor import extract_text_from_pdf_bytes
        pages, page_count, word_count = extract_text_from_pdf_bytes(path.read_bytes())
    else:
        raw = read_text_exact(path)
        if PAGE_BREAK in raw:
            chunks = [c.strip() for c in raw.split(PAGE_BREAK)]
        else:
            # Unpaginated text (converted benchmarks): keep it byte-exact so spans line up
            chunks = [raw]
        pages = [PageText(page_number=i + 1, text=c) for i, c in enumerate(chunks)]
        page_count = len(pages)
        word_count = sum(len(p.text.split()) for p in pages)

    return DocumentDetail(
        id=doc_id or f"eval_{re.sub(r'[^A-Za-z0-9]+', '_', path.stem)}",
        filename=path.name,
        page_count=page_count,
        word_count=word_count,
        uploadedAt="1970-01-01T00:00:00Z",
        status="ready",
        demo_mode=False,
        pages=pages,
    )


def find_span(full: str, text: str) -> Optional[Tuple[int, int]]:
    """Locates text in the document, ignoring whitespace and quote-style differences."""
    if not text.strip():
        return None
    idx = full.find(text)
    if idx >= 0:
        return idx, idx + len(text)
    quote = {'"': "[\"“”]", "“": "[\"“”]", "”": "[\"“”]", "'": "['‘’]", "’": "['‘’]", "‘": "['‘’]"}
    parts = []
    for tok in text.split():
        parts.append("".join(quote.get(ch, re.escape(ch)) for ch in tok))
    m = re.search(r"\s+".join(parts), full, re.IGNORECASE)
    return (m.start(), m.end()) if m else None


def resolve_spans(questions: List[Question], docs: Dict[str, object]) -> List[str]:
    """
    Fills in spans for gold items given only as text and checks given spans.
    Returns a list of problems (dataset errors).
    """
    from app.services.evidence.index import document_text

    problems = []
    texts = {name: document_text(doc) for name, doc in docs.items()}
    for q in questions:
        full = texts.get(q.contract)
        if full is None:
            problems.append(f"{q.qid}: contract '{q.contract}' not found")
            continue
        if q.answerable and not q.gold_evidence:
            problems.append(f"{q.qid}: answerable question has no gold evidence")
        for g in q.gold_evidence:
            if g.span is not None:
                s, e = g.span
                if not (0 <= s < e <= len(full)):
                    problems.append(f"{q.qid}: span {g.span} outside document ({len(full)} chars)")
                    g.span = None
                elif g.text and norm(full[s:e]) != norm(g.text):
                    problems.append(f"{q.qid}: span text does not match stored gold text at {g.span}")
                if not g.text and g.span:
                    g.text = full[s:e]
            else:
                g.span = find_span(full, g.text)
                if g.span is None:
                    problems.append(f"{q.qid}: gold text not in contract: {g.text[:60]!r}")
    return problems


def segmentation_warnings(questions: List[Question], indexes: Dict[str, object]) -> List[str]:
    """Gold spans that no single indexed clause fully contains (informational)."""
    out = []
    for q in questions:
        index = indexes.get(q.contract)
        if index is None:
            continue
        ranges = [(c.char_start, c.char_end) for c in index.clauses if c.char_start is not None]
        for g in q.gold_evidence:
            if g.span and not any(s <= g.span[0] and g.span[1] <= e for s, e in ranges):
                out.append(f"{q.qid}: gold span {g.span} crosses a clause boundary")
    return out
