"""
Builds the clause-level evidence index for one document.

Segmentation reuses the existing analysis chunker
(analysis_service.chunk_document_into_candidate_clauses) so top-level clause
boundaries match the Clauses tab. Each clause is then split further on:

- subsection headings such as "14.2 Termination for Cause" (the analysis
  chunker only recognises headings followed by "." or ":", e.g. "14.2. ...")
- attachment titles on their own line, e.g. "SCHEDULE 2 - SERVICE LEVELS"

Everything after the first attachment title is treated as attachment content:
its section numbers are kept on the record but are not used to resolve
cross-references in the main body.
"""

import logging
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.schemas.document import DocumentDetail
from app.services.analysis_service import chunk_document_into_candidate_clauses
from app.services.evidence import enrich
from app.services.evidence.bm25 import BM25

logger = logging.getLogger("lexiguard.evidence.index")

INDEX_VERSION = "1"

ATTACHMENT_TITLE_RE = re.compile(
    r"^[ \t]*(?P<kind>SCHEDULE|EXHIBIT|ANNEX|APPENDIX|ATTACHMENT|Schedule|Exhibit|Annex|Appendix|Attachment)"
    r"[ \t]+(?P<id>[A-Z0-9]{1,3})(?:[ \t]*[-–—:.][ \t]*[^\n]{0,100})?[ \t]*$",
    re.MULTILINE,
)


@dataclass
class ClauseRecord:
    id: str
    heading: str
    section: Optional[str]
    text: str
    page_start: int
    page_end: int
    page_span: str
    parent_id: Optional[str] = None
    attachment: Optional[str] = None          # e.g. "Schedule 2" if inside an attachment
    declares_terms: List[str] = field(default_factory=list)
    uses_terms: List[str] = field(default_factory=list)
    xrefs: List[str] = field(default_factory=list)
    xref_targets: Dict[str, Optional[str]] = field(default_factory=dict)
    attachment_refs: List[str] = field(default_factory=list)
    attachment_targets: Dict[str, Optional[str]] = field(default_factory=dict)
    modifiers: List[str] = field(default_factory=list)
    label: Optional[str] = None
    top_labels: List[Dict[str, Any]] = field(default_factory=list)
    # Character range in document_text(doc); None if the clause could not be located
    char_start: Optional[int] = None
    char_end: Optional[int] = None

    @property
    def search_text(self) -> str:
        if self.heading and not self.text.startswith(self.heading):
            return f"{self.heading}\n{self.text}"
        return self.text


@dataclass
class PageStats:
    page_number: int
    chars: int
    words: int
    low_text: bool


@dataclass
class EvidenceIndex:
    doc_id: str
    clauses: List[ClauseRecord]
    pages: List[PageStats]
    definitions: Dict[str, str]          # term -> defining clause id
    section_map: Dict[str, str]          # main-body section number -> clause id
    attachment_map: Dict[str, str]       # "Schedule 2" -> first clause id of that attachment
    bm25: BM25
    dense: Any = None                    # dense.DenseIndex or None
    build_info: Dict[str, Any] = field(default_factory=dict)

    def clause(self, clause_id: str) -> Optional[ClauseRecord]:
        return self._by_id().get(clause_id)

    def _by_id(self) -> Dict[str, ClauseRecord]:
        cache = getattr(self, "_id_cache", None)
        if cache is None or len(cache) != len(self.clauses):
            cache = {c.id: c for c in self.clauses}
            object.__setattr__(self, "_id_cache", cache)
        return cache

    def summary(self) -> Dict[str, Any]:
        """Small JSON-safe description for logs and the eval harness."""
        return {
            "doc_id": self.doc_id,
            "clauses": len(self.clauses),
            "definitions": len(self.definitions),
            "sections": len(self.section_map),
            "attachments": sorted(self.attachment_map),
            "unresolved_xrefs": sorted({
                ref for c in self.clauses for ref, target in c.xref_targets.items() if target is None
            }),
            "low_text_pages": [p.page_number for p in self.pages if p.low_text],
            "dense": None if self.dense is None else {"model": self.dense.model_name, "backend": self.dense.backend},
            **self.build_info,
        }

    def clause_dicts(self) -> List[Dict[str, Any]]:
        return [asdict(c) for c in self.clauses]


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    return " ".join((s or "").split())


def _locate_page(snippet: str, doc: DocumentDetail, first: int, last: int) -> int:
    """Finds the page (within first..last) on which a snippet of clause text occurs."""
    probe = _norm(snippet)[:60]
    if probe:
        for page in doc.pages:
            if first <= page.page_number <= last and probe in _norm(page.text):
                return page.page_number
    return first


def _split_piece(base: Dict[str, Any], doc: DocumentDetail) -> List[Dict[str, Any]]:
    """Splits one chunked clause on subsection headings and attachment titles."""
    text = base["text"]
    cuts = []
    for m in enrich.SUBSECTION_LINE_RE.finditer(text):
        if m.start() > 0:
            cuts.append((m.start(), "sub", m))
    for m in ATTACHMENT_TITLE_RE.finditer(text):
        cuts.append((m.start(), "att", m))
    cuts.sort(key=lambda x: x[0])
    if not cuts:
        return [dict(base, kind="base")]

    pieces: List[Dict[str, Any]] = []
    head_text = text[: cuts[0][0]].strip()
    if head_text:
        pieces.append(dict(base, text=head_text, kind="base"))

    for i, (start, kind, m) in enumerate(cuts):
        end = cuts[i + 1][0] if i + 1 < len(cuts) else len(text)
        seg = text[start:end].strip()
        if len(seg) < 15 and kind == "sub":
            continue
        first_line = seg.splitlines()[0].strip()
        if kind == "att":
            heading = first_line[:120]
            attachment = f"{m.group('kind').capitalize()} {m.group('id').upper()}"
        else:
            heading = re.split(r"(?<=[A-Za-z\)])\.\s", first_line, maxsplit=1)[0][:120]
            attachment = None
        page = _locate_page(seg, doc, base["page_start"], base["page_end"])
        last_page = max(page, _locate_page(seg[-60:], doc, page, base["page_end"]))
        pieces.append(dict(
            base,
            heading=heading,
            text=seg,
            page_start=page,
            page_end=last_page,
            page_span=str(page) if page == last_page else f"{page}-{last_page}",
            kind=kind,
            attachment=attachment,
        ))
    return pieces


def _preamble(doc: DocumentDetail, first_clause: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Text before the first numbered heading (title, parties, recitals). The
    analysis chunker discards it, but it often holds the party definitions.
    """
    probe = first_clause["text"][:40]
    parts = []
    for page in doc.pages:
        text = page.text or ""
        if page.page_number < first_clause["page_start"]:
            parts.append((page.page_number, text))
        elif page.page_number == first_clause["page_start"]:
            idx = text.find(probe)
            if idx > 0:
                parts.append((page.page_number, text[:idx]))
            break
    body = "\n".join(t for _, t in parts).strip()
    if len(body) < 30:
        return None
    pages = [n for n, t in parts if t.strip()]
    first, last = min(pages), max(pages)
    return {
        "heading": "Preamble",
        "text": body,
        "page": first,
        "page_start": first,
        "page_end": last,
        "page_span": str(first) if first == last else f"{first}-{last}",
    }


def segment_document(doc: DocumentDetail) -> List[ClauseRecord]:
    base_clauses = chunk_document_into_candidate_clauses(doc, max_clauses=settings.EVIDENCE_MAX_CLAUSES)
    if base_clauses:
        pre = _preamble(doc, dict(base_clauses[0], page_start=base_clauses[0].get("page_start", base_clauses[0]["page"])))
        if pre:
            base_clauses = [pre] + base_clauses
    records: List[ClauseRecord] = []
    current_attachment: Optional[str] = None
    parent_id: Optional[str] = None

    for base in base_clauses:
        base = dict(
            base,
            page_start=base.get("page_start", base["page"]),
            page_end=base.get("page_end", base["page"]),
        )
        parent_section = enrich.parse_section_number(base["heading"])
        for piece in _split_piece(base, doc):
            if piece["kind"] == "att":
                current_attachment = piece["attachment"]
            section = None if piece["kind"] == "att" else enrich.parse_section_number(piece["heading"])
            if piece["kind"] == "base" and section is None:
                section = parent_section
            heading = _norm(piece["heading"])
            first_part_id: Optional[str] = None
            windows = split_oversized(piece["text"], settings.EVIDENCE_MAX_CLAUSE_CHARS)
            for part_no, text in enumerate(windows, 1):
                page = _locate_page(text, doc, piece["page_start"], piece["page_end"])
                last_page = max(page, _locate_page(text[-60:], doc, page, piece["page_end"]))
                rec = ClauseRecord(
                    id=f"ev-{len(records) + 1:03d}",
                    heading=heading if part_no == 1 else f"{heading} (part {part_no})",
                    section=section,
                    text=text,
                    page_start=page if len(windows) > 1 else piece["page_start"],
                    page_end=last_page if len(windows) > 1 else piece["page_end"],
                    page_span=(str(page) if page == last_page else f"{page}-{last_page}") if len(windows) > 1 else piece["page_span"],
                    attachment=current_attachment,
                )
                if part_no > 1:
                    # Continuation of an oversized clause: the first part is its parent
                    rec.parent_id = first_part_id
                elif piece["kind"] == "sub":
                    rec.parent_id = parent_id
                else:
                    parent_id = rec.id
                if part_no == 1:
                    first_part_id = rec.id
                records.append(rec)
    return records


# Boundaries tried in order when splitting an oversized clause
_SPLIT_LEVELS = [
    re.compile(r"\n[ \t]*\n\s*"),                 # blank line (paragraph)
    re.compile(r"\n\s*"),                         # line break
    re.compile(r"(?<=[.;:])\s+(?=[A-Z(\"“])"),    # sentence / list-item end
    re.compile(r"(?<=[,])\s+"),                   # comma
]


def split_oversized(text: str, max_chars: int, min_chars: Optional[int] = None) -> List[str]:
    """
    Splits text longer than max_chars into consecutive windows of at most
    max_chars, cutting at the coarsest boundary available (paragraph, line,
    sentence, comma, then whitespace). Every window is an exact substring of
    the input, so character offsets stay recoverable. max_chars <= 0 disables it.
    """
    text = text.strip()
    if max_chars <= 0 or len(text) <= max_chars:
        return [text] if text else []
    min_chars = max_chars // 5 if min_chars is None else min_chars
    spans = _windows(text, 0, len(text), max_chars, 0)
    # Fold a too-small trailing window into its neighbour when that stays near the cap
    if len(spans) > 1 and spans[-1][1] - spans[-1][0] < min_chars and spans[-1][1] - spans[-2][0] <= max_chars + min_chars:
        spans[-2:] = [(spans[-2][0], spans[-1][1])]
    out = [text[s:e].strip() for s, e in spans]
    return [t for t in out if t]


def _windows(text: str, start: int, end: int, max_chars: int, level: int) -> List[tuple]:
    if end - start <= max_chars:
        return [(start, end)]
    if level >= len(_SPLIT_LEVELS):
        # Last resort: cut at the last whitespace before the limit
        out, s = [], start
        while end - s > max_chars:
            cut = text.rfind(" ", s + max_chars // 2, s + max_chars)
            cut = cut if cut > s else s + max_chars
            out.append((s, cut))
            s = cut
        out.append((s, end))
        return out

    cuts = [m.end() for m in _SPLIT_LEVELS[level].finditer(text, start, end) if start < m.end() < end]
    if not cuts:
        return _windows(text, start, end, max_chars, level + 1)
    bounds = [start] + cuts + [end]
    units = list(zip(bounds[:-1], bounds[1:]))

    out: List[tuple] = []
    cur_s, cur_e = None, None
    for us, ue in units:
        if ue - us > max_chars:
            if cur_s is not None:
                out.append((cur_s, cur_e))
                cur_s = None
            out.extend(_windows(text, us, ue, max_chars, level + 1))
        elif cur_s is None:
            cur_s, cur_e = us, ue
        elif ue - cur_s <= max_chars:
            cur_e = ue
        else:
            out.append((cur_s, cur_e))
            cur_s, cur_e = us, ue
    if cur_s is not None:
        out.append((cur_s, cur_e))
    return out


def document_text(doc: DocumentDetail) -> str:
    """The document text exactly as the analysis chunker joins it (non-empty pages, "\\n" between)."""
    return "\n".join(p.text for p in doc.pages if p.text)


def _locate(full: str, text: str, start: int) -> Optional[tuple]:
    """Finds text in full at or after start; falls back to whitespace-insensitive matching."""
    idx = full.find(text, start)
    if idx >= 0:
        return idx, idx + len(text)
    tokens = text.split()
    if not tokens:
        return None
    pattern = re.compile(r"\s+".join(re.escape(t) for t in tokens))
    m = pattern.search(full, start)
    if m:
        return m.start(), m.end()
    m = pattern.search(full)  # out-of-order segments (rare)
    return (m.start(), m.end()) if m else None


def assign_char_offsets(doc: DocumentDetail, clauses: List[ClauseRecord]) -> Dict[str, Any]:
    """
    Records each clause's character range in document_text(doc), and how much
    of the document the clauses cover. Clauses are located in document order;
    the paragraph-fallback chunker collapses whitespace, hence the fuzzy match.
    """
    full = document_text(doc)
    cursor = 0
    unlocated = 0
    for c in clauses:
        found = _locate(full, c.text.strip(), cursor)
        if found is None:
            unlocated += 1
            continue
        c.char_start, c.char_end = found
        cursor = max(cursor, c.char_start)
    covered = _covered_chars([(c.char_start, c.char_end) for c in clauses if c.char_start is not None])
    non_ws = len(full) - sum(ch.isspace() for ch in full)
    return {
        "doc_chars": len(full),
        "unlocated_clauses": unlocated,
        # share of document characters that fall inside some clause
        "char_coverage": round(covered / len(full), 4) if full else 0.0,
        "non_whitespace_chars": non_ws,
    }


def _covered_chars(ranges: List[tuple]) -> int:
    total, last_end = 0, -1
    for s, e in sorted(ranges):
        if e <= last_end:
            continue
        total += e - max(s, last_end)
        last_end = e
    return total


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------

def _page_stats(doc: DocumentDetail) -> List[PageStats]:
    raw = [(p.page_number, len((p.text or "").strip()), len((p.text or "").split())) for p in doc.pages]
    avg = (sum(c for _, c, _ in raw) / len(raw)) if raw else 0
    return [PageStats(n, c, w, low_text=(avg > 500 and c < 100)) for n, c, w in raw]


def enrich_clauses(clauses: List[ClauseRecord]) -> Dict[str, Dict[str, str]]:
    """Fills structural fields on each clause; returns the lookup maps."""
    section_map: Dict[str, str] = {}
    attachment_map: Dict[str, str] = {}
    definitions: Dict[str, str] = {}

    for c in clauses:
        if c.attachment is None and c.section and c.section not in section_map:
            section_map[c.section] = c.id
        if c.attachment and c.attachment not in attachment_map:
            attachment_map[c.attachment] = c.id
        c.declares_terms = enrich.extract_declared_terms(c.text)
        for term in c.declares_terms:
            definitions.setdefault(term, c.id)

    all_terms = sorted(definitions, key=len, reverse=True)
    for c in clauses:
        own = set(c.declares_terms)
        c.uses_terms = [t for t in enrich.find_term_uses(c.text, all_terms) if t not in own]
        c.xrefs = []
        c.xref_targets = {}
        for ref in enrich.extract_cross_references(c.text):
            if c.section and ref == c.section:
                continue  # "under this Section 14.2" inside 14.2
            target = enrich.resolve_section(ref, section_map)
            if target == c.id:
                continue
            c.xrefs.append(ref)
            c.xref_targets[ref] = target
        c.attachment_refs = [a for a in enrich.extract_attachment_references(c.text) if a != c.attachment]
        c.attachment_targets = {a: attachment_map.get(a) for a in c.attachment_refs}
        c.modifiers = enrich.extract_modifiers(c.text)

    return {"section_map": section_map, "attachment_map": attachment_map, "definitions": definitions}


def _classify(clauses: List[ClauseRecord]) -> Optional[str]:
    """Attaches LEDGAR labels. Slow on CPU (ModernBERT-large), so off by default."""
    try:
        from app.services.classifier_service import classifier_service
        for c in clauses:
            pred = classifier_service.classify(c.text, top_k=3)
            c.label = pred.get("predicted_category")
            c.top_labels = pred.get("top_predictions", [])
        return None
    except Exception as e:  # pragma: no cover - environment dependent
        logger.warning("Classifier labels unavailable for evidence index: %s", e)
        return str(e)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_evidence_index(doc: DocumentDetail, with_dense: bool = False, with_labels: Optional[bool] = None) -> EvidenceIndex:
    t0 = time.perf_counter()
    clauses = segment_document(doc)
    offsets_info = assign_char_offsets(doc, clauses)
    maps = enrich_clauses(clauses)
    label_error = None
    if with_labels if with_labels is not None else settings.EVIDENCE_CLASSIFY_AT_INDEX:
        label_error = _classify(clauses)

    index = EvidenceIndex(
        doc_id=doc.id,
        clauses=clauses,
        pages=_page_stats(doc),
        definitions=maps["definitions"],
        section_map=maps["section_map"],
        attachment_map=maps["attachment_map"],
        bm25=BM25([c.search_text for c in clauses]),
        build_info={
            "index_version": INDEX_VERSION,
            "label_error": label_error,
            # the analysis chunker stops at EVIDENCE_MAX_CLAUSES top-level clauses
            "clause_cap": settings.EVIDENCE_MAX_CLAUSES,
            "max_clause_chars": settings.EVIDENCE_MAX_CLAUSE_CHARS,
            "longest_clause_chars": max((len(c.text) for c in clauses), default=0),
            **offsets_info,
        },
    )
    index.build_info["build_seconds_structural"] = round(time.perf_counter() - t0, 3)
    if with_dense:
        ensure_dense(index)
    return index


def ensure_dense(index: EvidenceIndex) -> bool:
    """Adds dense embeddings to an index if they are not there yet. Returns True if available."""
    if index.dense is not None:
        return True
    from app.services.evidence import dense
    t0 = time.perf_counter()
    index.dense = dense.build_dense_index([c.search_text for c in index.clauses])
    index.build_info["build_seconds_dense"] = round(time.perf_counter() - t0, 3)
    if index.dense is None:
        index.build_info["dense_error"] = dense.load_errors().get("embedder", "no clauses")
    return index.dense is not None
