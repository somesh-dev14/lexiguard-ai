"""
Metric helpers. All metrics are computed from recorded per-question data, so
summaries can be recomputed from per_question.jsonl without rerunning.
"""

import re
from statistics import mean
from typing import Dict, Iterable, List, Optional

from dataset import norm

# Heuristic abstention detector for generated answers. It is only a screening
# aid: final judgments belong in the manual grading sheet.
ABSTAIN_RE = re.compile(
    r"does not (?:explicitly |expressly )?(?:contain|specify|mention|address|provide|include|state|restrict|require|grant|cover)|"
    r"\bno (?:[a-z\-]+ ){0,3}(?:information|provision|mention|clause|term|right|restriction)s? (?:is |are )?(?:present|found|included|provided|exists?)|"
    r"\bno (?:information|provision|mention|clause)|not (?:specified|mentioned|addressed|stated|covered|found)|"
    r"cannot be determined|is silent",
    re.IGNORECASE,
)


def _overlap(a: tuple, b: tuple) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def _union_len(ranges: List[tuple]) -> int:
    total, last = 0, -1
    for s, e in sorted(ranges):
        if e <= last:
            continue
        total += e - max(s, last)
        last = e
    return total


def _covered(span: tuple, ranges: List[tuple]) -> int:
    """Characters of span covered by the union of ranges."""
    clipped = [(max(s, span[0]), min(e, span[1])) for s, e in ranges if _overlap((s, e), span) > 0]
    return _union_len(clipped)


def gold_ranks(gold_spans: List[Optional[tuple]], ranked_ranges: List[Optional[tuple]], threshold: float = 0.5) -> List[Optional[int]]:
    """
    For each gold span, the smallest k such that the top-k retrieved clauses
    together cover at least `threshold` of its characters (None if never).
    A gold span split across two clauses counts once both are retrieved.
    """
    out = []
    for g in gold_spans:
        if g is None or g[1] <= g[0]:
            out.append(None)
            continue
        need = threshold * (g[1] - g[0])
        rank = None
        acc: List[tuple] = []
        for i, r in enumerate(ranked_ranges):
            if r is None:
                continue
            acc.append(r)
            if _covered(g, acc) >= need - 1e-9:
                rank = i + 1
                break
        out.append(rank)
    return out


def char_precision_recall(gold_spans: List[Optional[tuple]], ranked_ranges: List[Optional[tuple]], k: int) -> Dict[str, float]:
    """LegalBench-RAG-style character-level precision and recall of the top-k clauses."""
    gold = [g for g in gold_spans if g]
    top = [r for r in ranked_ranges[:k] if r]
    gold_len = _union_len(gold)
    ret_len = _union_len(top)
    inter = sum(_covered(g, top) for g in _merge(gold))
    return {
        "char_recall": inter / gold_len if gold_len else 0.0,
        "char_precision": inter / ret_len if ret_len else 0.0,
    }


def fill_budget(lengths: List[int], budget: int, separator: int = 80) -> List[tuple]:
    """
    Clauses (in rank order) that fit a character budget, as (index, chars_taken).
    Like the app's format_context, a clause that does not fit is skipped and
    later, smaller ones may still be added. Unlike the app, a first clause larger
    than the whole budget counts only for its first `budget` characters, so a
    single giant clause cannot "cover" evidence the prompt could not hold.
    `separator` approximates the per-clause header the prompt adds.
    """
    chosen, total = [], 0
    for i, n in enumerate(lengths):
        cost = n + separator
        if not chosen and cost > budget:
            chosen.append((i, max(0, budget - separator)))
            total = budget
            continue
        if total + cost > budget:
            continue
        chosen.append((i, n))
        total += cost
    return chosen


def _merge(ranges: List[tuple]) -> List[tuple]:
    out: List[list] = []
    for s, e in sorted(ranges):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [tuple(x) for x in out]


def at_k(ranks: List[Optional[int]], k: int) -> Dict[str, float]:
    found = [r is not None and r <= k for r in ranks]
    return {
        "hit": float(any(found)),
        "recall": (sum(found) / len(found)) if found else 0.0,
        "complete": float(all(found)) if found else 0.0,
    }


def reciprocal_rank(ranks: List[Optional[int]]) -> float:
    valid = [r for r in ranks if r is not None]
    return 1.0 / min(valid) if valid else 0.0


def summarize_retrieval(rows: Iterable[dict], ks: List[int]) -> Dict[str, dict]:
    """rows: per-question dicts with "answerable", "type", "gold_roles", "ranks"."""
    rows = [r for r in rows if r["answerable"] and r["ranks"]]
    if not rows:
        return {}
    summary = {"n": len(rows), "mrr": round(mean(reciprocal_rank(r["ranks"]) for r in rows), 4)}
    for k in ks:
        vals = [at_k(r["ranks"], k) for r in rows]
        summary[f"hit@{k}"] = round(mean(v["hit"] for v in vals), 4)
        summary[f"recall@{k}"] = round(mean(v["recall"] for v in vals), 4)
        summary[f"complete@{k}"] = round(mean(v["complete"] for v in vals), 4)
        if all(f"char@{k}" in r for r in rows):
            summary[f"char_recall@{k}"] = round(mean(r[f"char@{k}"]["char_recall"] for r in rows), 4)
            summary[f"char_precision@{k}"] = round(mean(r[f"char@{k}"]["char_precision"] for r in rows), 4)
        # Primary evidence vs dependency evidence (definitions, cross-refs, overrides, attachments)
        for role_group, roles in (("primary", {"primary"}), ("dependency", {"definition", "xref", "override", "attachment"})):
            items = [
                (rank is not None and rank <= k)
                for r in rows for rank, role in zip(r["ranks"], r["gold_roles"]) if role in roles
            ]
            if items:
                summary[f"{role_group}_recall@{k}"] = round(sum(items) / len(items), 4)
                summary[f"{role_group}_items"] = len(items)
    by_type = {}
    for t in sorted({r["type"] for r in rows}):
        sub = [r for r in rows if r["type"] == t]
        by_type[t] = {
            "n": len(sub),
            **{f"complete@{k}": round(mean(at_k(r["ranks"], k)["complete"] for r in sub), 4) for k in ks},
        }
    summary["by_type"] = by_type
    return summary


def citation_hits_gold(excerpts: List[str], gold_texts: List[str]) -> bool:
    """True if any cited excerpt overlaps any gold evidence text."""
    for e in excerpts:
        ne = norm(e)
        if len(ne) < 6:
            continue
        te = set(re.findall(r"[a-z0-9]+", ne))
        for g in gold_texts:
            ng = norm(g)
            if ng in ne or ne in ng:
                return True
            tg = set(re.findall(r"[a-z0-9]+", ng))
            if te and tg and len(te & tg) / min(len(te), len(tg)) >= 0.6:
                return True
    return False
