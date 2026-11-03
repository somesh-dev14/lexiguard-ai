"""
Plain one-shot clause retrieval: the B1 baseline.

BM25 and dense rankings are fused with reciprocal rank fusion (RRF); the top
candidate pool is then optionally reranked with a cross-encoder. No
sufficiency check, no gap detection, no second round: this is the comparison
point the evidence controller must beat.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.evidence.index import ClauseRecord, EvidenceIndex, ensure_dense


@dataclass
class RetrievalHit:
    clause_id: str
    rank: int
    bm25_score: float
    bm25_rank: Optional[int]
    dense_score: Optional[float]
    dense_rank: Optional[int]
    rrf_score: float
    rerank_score: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _ranks(scored: List[tuple]) -> Dict[int, int]:
    """scored: list of (idx, score), already sorted best-first -> {idx: 1-based rank}."""
    return {idx: r + 1 for r, (idx, _) in enumerate(scored)}


def retrieve(
    index: EvidenceIndex,
    query: str,
    top_k: Optional[int] = None,
    use_bm25: bool = True,
    use_dense: Optional[bool] = None,
    use_rerank: Optional[bool] = None,
    pool: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Returns {"hits": [RetrievalHit...], "components": {...}} ordered best-first.
    Flags default to the QA settings; the eval harness overrides them for ablations.
    """
    top_k = top_k or settings.EVIDENCE_TOP_K
    pool = pool or settings.EVIDENCE_CANDIDATE_POOL
    use_dense = settings.EVIDENCE_DENSE_ENABLED if use_dense is None else use_dense
    use_rerank = settings.EVIDENCE_RERANK_ENABLED if use_rerank is None else use_rerank
    n = len(index.clauses)
    components = {"bm25": False, "dense": False, "rerank": False}
    if n == 0:
        return {"hits": [], "components": components}

    bm25_scores = index.bm25.scores(query)
    bm25_sorted = sorted(
        [(i, s) for i, s in enumerate(bm25_scores) if s > 0], key=lambda x: x[1], reverse=True
    )
    bm25_rank = _ranks(bm25_sorted) if use_bm25 else {}
    components["bm25"] = use_bm25

    dense_scores: Dict[int, float] = {}
    dense_rank: Dict[int, int] = {}
    if use_dense and ensure_dense(index):
        from app.services.evidence import dense
        qv = dense.embed_query(query)
        if qv is not None:
            found = index.dense.search(qv, n)
            dense_scores = {i: s for i, s in found}
            dense_rank = _ranks(found)
            components["dense"] = True

    # Reciprocal rank fusion over whichever rankings are active
    k = settings.EVIDENCE_RRF_K
    fused: Dict[int, float] = {}
    for ranking in (bm25_rank, dense_rank):
        for idx, r in ranking.items():
            if r <= pool:
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + r)
    order = sorted(fused, key=lambda i: fused[i], reverse=True)[:pool]

    rerank: Dict[int, float] = {}
    if use_rerank and order:
        from app.services.evidence import dense
        scores = dense.rerank_scores(query, [index.clauses[i].search_text for i in order])
        if scores is not None:
            rerank = dict(zip(order, scores))
            order = sorted(order, key=lambda i: rerank[i], reverse=True)
            components["rerank"] = True

    hits = [
        RetrievalHit(
            clause_id=index.clauses[i].id,
            rank=r + 1,
            bm25_score=round(bm25_scores[i], 4),
            bm25_rank=bm25_rank.get(i),
            dense_score=None if i not in dense_scores else round(dense_scores[i], 4),
            dense_rank=dense_rank.get(i),
            rrf_score=round(fused[i], 6),
            rerank_score=None if i not in rerank else round(rerank[i], 4),
        )
        for r, i in enumerate(order[:top_k])
    ]
    return {"hits": hits, "components": components}


def format_context(index: EvidenceIndex, hits: List[RetrievalHit], max_chars: Optional[int] = None) -> Dict[str, Any]:
    """
    Formats retrieved clauses for the answer prompt, best-first, within a
    character budget. Clauses are never cut mid-text: a clause that does not
    fit is skipped and reported in "dropped".
    """
    max_chars = max_chars or settings.EVIDENCE_MAX_CONTEXT_CHARS
    blocks, used, dropped = [], [], []
    total = 0
    for h in hits:
        c: ClauseRecord = index.clause(h.clause_id)
        block = f"--- Page {c.page_span} | {c.heading} ---\n{c.text.strip()}"
        if total + len(block) > max_chars and blocks:
            dropped.append(h.clause_id)
            continue
        blocks.append(block)
        used.append(h.clause_id)
        total += len(block) + 2
    return {"context": "\n\n".join(blocks), "used": used, "dropped": dropped}
