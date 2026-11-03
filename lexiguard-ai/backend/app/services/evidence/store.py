"""
In-memory evidence index store, keyed by document id.

Kept separate from documents._documents_store so the DocumentDetail schema
returned to the frontend does not change.
"""

import logging
import threading
from typing import Dict, Optional

from app.schemas.document import DocumentDetail
from app.services.evidence.index import EvidenceIndex, build_evidence_index, ensure_dense

logger = logging.getLogger("lexiguard.evidence.store")

_store: Dict[str, EvidenceIndex] = {}
_lock = threading.Lock()


def index_document(doc: DocumentDetail, with_dense: bool = False) -> EvidenceIndex:
    index = build_evidence_index(doc, with_dense=with_dense)
    with _lock:
        _store[doc.id] = index
    logger.info("Evidence index built for %s: %s", doc.id, index.summary())
    return index


def get(doc_id: str) -> Optional[EvidenceIndex]:
    return _store.get(doc_id)


def get_or_build(doc: DocumentDetail, with_dense: bool = False) -> EvidenceIndex:
    index = _store.get(doc.id)
    if index is None:
        index = index_document(doc, with_dense=with_dense)
    elif with_dense:
        ensure_dense(index)
    return index


def remove(doc_id: str) -> None:
    with _lock:
        _store.pop(doc_id, None)


def clear() -> None:
    with _lock:
        _store.clear()
