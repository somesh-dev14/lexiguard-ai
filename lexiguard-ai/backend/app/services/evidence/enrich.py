"""
Structural enrichment of clause text.

Pure-regex extraction of the contract structure the later evidence controller
will need. Everything here is deterministic and cheap; no ML.

- section numbers from clause headings ("14.2 Termination for Cause" -> "14.2")
- defined terms a clause declares ("Early Termination Fee" means ...)
- defined terms a clause uses
- cross-references ("subject to Section 12.3", "Schedule 2")
- override / exception markers ("notwithstanding", "subject to", ...)

Known limits (deliberately conservative):
- Only quoted definitions are detected. Unquoted parentheticals such as
  "(Provider)" are ambiguous and are ignored.
- Cross-references to sub-paragraphs ("Section 4.2(b)") resolve to the
  closest indexed section ("4.2", else "4").
"""

import re
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Section numbers
# ---------------------------------------------------------------------------

_SECTION_NUM_RE = re.compile(
    r"^\s*(?:(?:Section|Article|Clause)\s+)?(?P<num>\d{1,3}(?:\.\d{1,3})*)[\.\:\)]?(?=\s|$)",
    re.IGNORECASE,
)

# Subsection headings inside a clause, e.g. "14.2 Termination for Cause."
# Requires at least one dot in the number so plain list items ("1 ") are not split.
SUBSECTION_LINE_RE = re.compile(
    r"^[ \t]*(?P<num>\d{1,3}(?:\.\d{1,3})+)\.?[ \t]+(?=[A-Z\"“(])",
    re.MULTILINE,
)


def parse_section_number(heading: str) -> Optional[str]:
    """Returns the normalized section number of a clause heading, or None."""
    if not heading:
        return None
    m = _SECTION_NUM_RE.match(heading)
    if not m:
        return None
    return m.group("num").strip(".")


# ---------------------------------------------------------------------------
# Defined terms
# ---------------------------------------------------------------------------

_Q_OPEN = r"[\"“]"
_Q_CLOSE = r"[\"”]"
_TERM = r"(?P<term>[A-Z][A-Za-z0-9\-'’]*(?:\s+[A-Za-z0-9\-'’]+){0,6}?)"

_DEFINITION_PATTERNS = [
    # "Early Termination Fee" means / shall mean / has the meaning / refers to / includes
    re.compile(
        _Q_OPEN + _TERM + _Q_CLOSE
        + r"\s*(?:,\s*)?(?:shall\s+)?(?:means?|mean|has\s+the\s+meaning|shall\s+have\s+the\s+meaning|refers?\s+to|includes?)\b"
    ),
    # (the "Agreement") / ("Supplier") / (each, a "Party")
    re.compile(
        r"\(\s*(?:the\s+|each\s+|a\s+|an\s+|each,\s+a\s+|together,\s+the\s+|collectively,\s+the\s+)?"
        + _Q_OPEN + _TERM + _Q_CLOSE + r"\s*\)"
    ),
]


def extract_declared_terms(text: str) -> List[str]:
    """Returns defined terms declared in this text, in order of appearance."""
    found: Dict[int, str] = {}
    for pat in _DEFINITION_PATTERNS:
        for m in pat.finditer(text or ""):
            term = " ".join(m.group("term").split())
            if 1 <= len(term) <= 60:
                found.setdefault(m.start(), term)
    seen = set()
    ordered = []
    for _, term in sorted(found.items()):
        if term not in seen:
            seen.add(term)
            ordered.append(term)
    return ordered


def find_term_uses(text: str, terms: List[str]) -> List[str]:
    """Returns which of the given defined terms occur in the text (case-sensitive, whole word)."""
    uses = []
    for term in terms:
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", text or ""):
            uses.append(term)
    return uses


# ---------------------------------------------------------------------------
# Cross-references and attachments
# ---------------------------------------------------------------------------

_XREF_RE = re.compile(
    r"\b(?:Sections?|Clauses?|Articles?|Paragraphs?)\s+"
    r"(?P<num>\d{1,3}(?:\.\d{1,3})*)(?P<sub>(?:\([a-z0-9]{1,4}\))*)",
)
# "Sections 8 and 11.1" / "Sections 8, 9 or 11.1": capture the extra numbers after the first
_XREF_LIST_TAIL_RE = re.compile(
    r"^(?:\s*(?:,|and|or|,\s*and|,\s*or)\s*(?P<num>\d{1,3}(?:\.\d{1,3})*)(?:\([a-z0-9]{1,4}\))*)"
)
_ATTACHMENT_RE = re.compile(
    r"\b(?P<kind>Schedule|Exhibit|Annex|Appendix|Attachment)\s+(?P<id>[A-Z0-9]{1,3})\b"
)


def extract_cross_references(text: str) -> List[str]:
    """Returns referenced section numbers (e.g. ["12.3", "14.2"]), without duplicates."""
    refs: List[str] = []
    text = text or ""
    for m in _XREF_RE.finditer(text):
        refs.append(m.group("num").strip("."))
        tail = text[m.end():]
        while True:
            t = _XREF_LIST_TAIL_RE.match(tail)
            if not t:
                break
            refs.append(t.group("num").strip("."))
            tail = tail[t.end():]
    out, seen = [], set()
    for r in refs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def extract_attachment_references(text: str) -> List[str]:
    """Returns referenced attachments normalized as "Schedule 2", "Exhibit A"."""
    out, seen = [], set()
    for m in _ATTACHMENT_RE.finditer(text or ""):
        ref = f"{m.group('kind').capitalize()} {m.group('id')}"
        if ref not in seen:
            seen.add(ref)
            out.append(ref)
    return out


def resolve_section(ref: str, section_map: Dict[str, str]) -> Optional[str]:
    """
    Maps a referenced section number to a clause id. Tries the exact number,
    then progressively shorter prefixes ("4.2.1" -> "4.2" -> "4").
    """
    parts = ref.split(".")
    while parts:
        key = ".".join(parts)
        if key in section_map:
            return section_map[key]
        parts = parts[:-1]
    return None


# ---------------------------------------------------------------------------
# Override / exception markers
# ---------------------------------------------------------------------------

MODIFIER_PATTERNS = {
    "notwithstanding": re.compile(r"\bnotwithstanding\b", re.IGNORECASE),
    "subject_to": re.compile(r"\bsubject\s+to\b", re.IGNORECASE),
    "except_as_provided": re.compile(r"\bexcept\s+(?:as\s+(?:otherwise\s+)?(?:provided|set\s+out|stated)|that)\b", re.IGNORECASE),
    "in_lieu_of": re.compile(r"\bin\s+lieu\s+of\b", re.IGNORECASE),
    "supersedes": re.compile(r"\bsupersed(?:e|es|ed|ing)\b", re.IGNORECASE),
    "prevails": re.compile(r"\bshall\s+prevail\b|\btake\s+precedence\b", re.IGNORECASE),
    "without_prejudice": re.compile(r"\bwithout\s+prejudice\s+to\b", re.IGNORECASE),
    "shall_not_apply": re.compile(r"\bshall\s+not\s+apply\b", re.IGNORECASE),
}


def extract_modifiers(text: str) -> List[str]:
    """Returns the override/exception marker types present in the text."""
    return [name for name, pat in MODIFIER_PATTERNS.items() if pat.search(text or "")]
