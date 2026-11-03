from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.schemas.document import UploadResponse, DocumentDetail
from app.services.pdf_extractor import extract_text_from_pdf_bytes, PDFExtractionError
from app.services.analysis_service import get_demo_analysis_for_document
from app.core.config import settings
from app.services.evidence import store as evidence_store
import anyio
import logging
import uuid
from datetime import datetime
from typing import Dict

router = APIRouter(prefix="/documents", tags=["Documents"])

logger = logging.getLogger("lexiguard.documents")

_documents_store: Dict[str, DocumentDetail] = {}

@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported."
        )

    content = await file.read()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
        )

    try:
        pages, page_count, word_count = extract_text_from_pdf_bytes(content)
    except PDFExtractionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    uploaded_at = datetime.utcnow().isoformat() + "Z"

    doc_detail = DocumentDetail(
        id=doc_id,
        filename=file.filename,
        page_count=page_count,
        word_count=word_count,
        uploadedAt=uploaded_at,
        status="ready",
        demo_mode=(settings.AI_MODE == "demo"),
        pages=pages
    )
    _documents_store[doc_id] = doc_detail

    # Upload-time evidence index (experimental). Structural + BM25 parts are cheap;
    # dense embeddings are only built here when a retrieval QA mode is active.
    # Indexing must never fail an upload.
    try:
        await anyio.to_thread.run_sync(
            evidence_store.index_document,
            doc_detail,
            settings.QA_MODE.lower() != "baseline",
        )
    except Exception as e:
        logger.warning("Evidence indexing failed for %s: %s", doc_id, e)

    return doc_detail

@router.get("/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: str):
    if doc_id not in _documents_store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return _documents_store[doc_id]

from app.services.analysis_service import get_document_analysis
from app.services.chat_service import answer_document_question

@router.get("/{doc_id}/analysis")
async def get_analysis(doc_id: str):
    if doc_id not in _documents_store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        return await get_document_analysis(_documents_store[doc_id])
    except TimeoutError as te:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"AI analysis timed out: {str(te)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis processing error: {str(e)}"
        )


@router.post("/{doc_id}/chat")
async def chat_with_document(doc_id: str, body: dict):
    """Answer a question about a specific document using its extracted text."""
    if doc_id not in _documents_store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is required"
        )

    doc = _documents_store[doc_id]
    try:
        result = await answer_document_question(doc, question)
        return result
    except TimeoutError as te:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"AI chat timed out: {str(te)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing error: {str(e)}"
        )


@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    if doc_id in _documents_store:
        del _documents_store[doc_id]
    evidence_store.remove(doc_id)
    return {"success": True}
