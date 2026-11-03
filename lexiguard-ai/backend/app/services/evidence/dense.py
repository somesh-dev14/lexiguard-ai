"""
Dense embeddings and cross-encoder reranking (loaded lazily, CPU).

Heavy imports (torch, sentence-transformers, faiss) happen only on first use,
so baseline mode and uploads never pay the model-loading cost.

Like classifier_service, this relies on the system Python's site-packages for
torch / sentence-transformers / faiss, because the app venv does not include them.
"""

import logging
import os
import sys
import threading
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from app.core.config import settings

logger = logging.getLogger("lexiguard.evidence.dense")

_lock = threading.Lock()
_embedder = None
_reranker = None
_load_errors: dict = {}


def _ensure_ml_path() -> None:
    site = settings.ML_SITE_PACKAGES
    if site and Path(site).exists() and site not in sys.path:
        sys.path.append(site)
    if settings.EVIDENCE_MODELS_LOCAL_ONLY:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def get_embedder():
    """Returns the sentence embedding model, or None if it cannot be loaded."""
    global _embedder
    if _embedder is not None or "embedder" in _load_errors:
        return _embedder
    with _lock:
        if _embedder is None and "embedder" not in _load_errors:
            try:
                _ensure_ml_path()
                from sentence_transformers import SentenceTransformer
                _embedder = SentenceTransformer(
                    settings.EVIDENCE_EMBED_MODEL,
                    device="cpu",
                    local_files_only=settings.EVIDENCE_MODELS_LOCAL_ONLY,
                )
                logger.info("Loaded embedding model %s", settings.EVIDENCE_EMBED_MODEL)
            except Exception as e:  # pragma: no cover - environment dependent
                _load_errors["embedder"] = str(e)
                logger.warning("Dense retrieval unavailable: %s", e)
    return _embedder


def get_reranker():
    """Returns the cross-encoder reranker, or None if it cannot be loaded."""
    global _reranker
    if _reranker is not None or "reranker" in _load_errors:
        return _reranker
    with _lock:
        if _reranker is None and "reranker" not in _load_errors:
            try:
                _ensure_ml_path()
                from sentence_transformers import CrossEncoder
                _reranker = CrossEncoder(
                    settings.EVIDENCE_RERANK_MODEL,
                    device="cpu",
                    local_files_only=settings.EVIDENCE_MODELS_LOCAL_ONLY,
                )
                logger.info("Loaded reranker %s", settings.EVIDENCE_RERANK_MODEL)
            except Exception as e:  # pragma: no cover - environment dependent
                _load_errors["reranker"] = str(e)
                logger.warning("Cross-encoder reranking unavailable: %s", e)
    return _reranker


def load_errors() -> dict:
    return dict(_load_errors)


class DenseIndex:
    """Normalized embeddings with inner-product search (FAISS if available, else numpy)."""

    def __init__(self, vectors, model_name: str):
        self.model_name = model_name
        self.dim = int(vectors.shape[1])
        self._vectors = vectors
        self._faiss = None
        try:
            import faiss  # noqa: WPS433 (lazy import)
            index = faiss.IndexFlatIP(self.dim)
            index.add(vectors.astype("float32"))
            self._faiss = index
        except Exception as e:  # pragma: no cover - environment dependent
            logger.info("FAISS unavailable, using numpy search: %s", e)

    @property
    def backend(self) -> str:
        return "faiss" if self._faiss is not None else "numpy"

    def search(self, query_vec, top_n: int) -> List[Tuple[int, float]]:
        top_n = min(top_n, self._vectors.shape[0])
        if top_n <= 0:
            return []
        q = query_vec.reshape(1, -1).astype("float32")
        if self._faiss is not None:
            scores, ids = self._faiss.search(q, top_n)
            return [(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i >= 0]
        sims = (self._vectors @ q[0])
        order = sims.argsort()[::-1][:top_n]
        return [(int(i), float(sims[i])) for i in order]


def build_dense_index(texts: Sequence[str]) -> Optional[DenseIndex]:
    model = get_embedder()
    if model is None or not texts:
        return None
    vectors = model.encode(list(texts), normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    return DenseIndex(vectors, settings.EVIDENCE_EMBED_MODEL)


def embed_query(text: str):
    model = get_embedder()
    if model is None:
        return None
    return model.encode([text], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)[0]


def rerank_scores(query: str, texts: Sequence[str]) -> Optional[List[float]]:
    model = get_reranker()
    if model is None or not texts:
        return None
    scores = model.predict([(query, t) for t in texts], show_progress_bar=False)
    return [float(s) for s in scores]
