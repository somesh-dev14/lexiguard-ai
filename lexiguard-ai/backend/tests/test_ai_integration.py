"""
Unit and integration tests for AI components:
- Ollama response sanitization (stripping thinking tags, ignoring JSON thinking fields)
- ClassifierService initialization and inference mocking
- OllamaClient error and timeout handling
- Live vs. Demo analysis fallback behavior
- API compatibility with existing frontend schema
"""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.ollama_client import sanitize_ollama_response, OllamaClient
from app.services.classifier_service import ClassifierService
from app.services.analysis_service import (
    get_document_analysis,
    get_demo_analysis_for_document,
    chunk_document_into_candidate_clauses
)
from app.schemas.document import DocumentDetail, PageText
from app.core.config import settings

client = TestClient(app)


def test_sanitize_ollama_response():
    # 1. Output containing <think>...</think>
    raw_with_think = "<think>The user wants a summary of the contract.\nLet's evaluate clauses.</think>This agreement is binding on both parties."
    assert sanitize_ollama_response(raw_with_think) == "This agreement is binding on both parties."

    # 2. Case insensitive and multiline
    raw_multiline = "<THINK>\nfirst line\nsecond line\n</THINK>\n\nConfidentiality obligations apply for 3 years."
    assert sanitize_ollama_response(raw_multiline) == "Confidentiality obligations apply for 3 years."

    # 3. Truncated mid-thought
    raw_truncated = "<think>Let me contemplate..."
    assert sanitize_ollama_response(raw_truncated) == ""

    # 4. Clean text with no think tags
    clean_text = "Governing law is Delaware."
    assert sanitize_ollama_response(clean_text) == "Governing law is Delaware."

    # 5. Output containing orphaned closing </think> tag preceded by thinking text
    raw_orphaned_close = "We are asked to summarize 2+2.\n The calculation is 2+2=4.\n</think>\n\n4"
    assert sanitize_ollama_response(raw_orphaned_close) == "4"


@pytest.mark.anyio
async def test_ollama_client_ignores_thinking_field():
    ollama = OllamaClient()
    mock_response = {
        "response": "<think>Internal deliberation</think>Summary of liability terms.",
        "thinking": "This is the separate Ollama thinking field that should never be shown.",
        "done": True
    }

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp_obj = MagicMock()
        mock_resp_obj.status_code = 200
        mock_resp_obj.json.return_value = mock_response
        mock_post.return_value = mock_resp_obj

        result = await ollama.generate(prompt="Summarize liability")
        assert result == "Summary of liability terms."
        assert "Internal deliberation" not in result
        assert "separate Ollama thinking" not in result


@pytest.mark.anyio
async def test_ollama_client_payload_configuration():
    # Test that think=False, num_predict, temperature, timeout, and ChatML bypass are correctly structured
    ollama = OllamaClient(
        timeout_seconds=45.0,
        num_predict=256,
        temperature=0.1,
        disable_thinking=True
    )

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp_obj = MagicMock()
        mock_resp_obj.status_code = 200
        mock_resp_obj.json.return_value = {"response": "Configured response"}
        mock_post.return_value = mock_resp_obj

        result = await ollama.generate(
            prompt="Analyze clause",
            system_prompt="Legal expert",
            options={"num_predict": 128}
        )

        assert result == "Configured response"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["model"] == settings.OLLAMA_MODEL
        assert payload["think"] is False
        assert payload["raw"] is True
        assert "<|im_start|>system\nLegal expert<|im_end|>" in payload["prompt"]
        assert "<|im_start|>user\nAnalyze clause<|im_end|>" in payload["prompt"]
        assert "<|im_start|>assistant\n<think>\nDone.\n</think>" in payload["prompt"]
        assert payload["options"]["num_predict"] == 128
        assert payload["options"]["temperature"] == 0.1
        assert "<|im_end|>" in payload["options"]["stop"]


@pytest.mark.anyio
async def test_ollama_client_non_qwen_or_thinking_enabled():
    # When disable_thinking is False, raw bypass is not used and think=True is sent
    ollama = OllamaClient(
        model="generic-model",
        disable_thinking=False
    )

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp_obj = MagicMock()
        mock_resp_obj.status_code = 200
        mock_resp_obj.json.return_value = {"response": "Clean response"}
        mock_post.return_value = mock_resp_obj

        result = await ollama.generate(
            prompt="Analyze clause",
            system_prompt="Legal expert"
        )

        assert result == "Clean response"
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["prompt"] == "Analyze clause"
        assert payload["system"] == "Legal expert"
        assert payload["think"] is True
        assert "raw" not in payload


@pytest.mark.anyio
async def test_ollama_client_timeout_handling():
    ollama = OllamaClient(timeout_seconds=1.0)
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timed out")):
        with pytest.raises(TimeoutError) as exc_info:
            await ollama.generate(prompt="Test timeout")
        assert "timed out" in str(exc_info.value).lower()


@pytest.mark.anyio
async def test_ollama_client_http_500_surfaces_error_detail():
    ollama = OllamaClient()
    mock_resp_obj = MagicMock()
    mock_resp_obj.is_error = True
    mock_resp_obj.status_code = 500
    mock_resp_obj.text = '{"error": "llama-server process has terminated: exit status 0xc0000409: CUDA error: shared object initialization failed"}'

    with patch("httpx.AsyncClient.post", return_value=mock_resp_obj), \
         patch("app.services.ollama_client.logger.error") as mock_log_err:
        with pytest.raises(RuntimeError) as exc_info:
            await ollama.generate(prompt="CONFIDENTIAL LEGAL CONTRACT TEXT")

        err_msg = str(exc_info.value)
        assert "status 500" in err_msg
        assert "CUDA error: shared object initialization failed" in err_msg
        assert "CONFIDENTIAL LEGAL CONTRACT TEXT" not in err_msg
        mock_log_err.assert_called_once()
        log_args = mock_log_err.call_args[0]
        # Verify log message does not leak prompt content
        for arg in log_args:
            assert "CONFIDENTIAL LEGAL CONTRACT TEXT" not in str(arg)


def test_classifier_service_singleton_mocked():
    svc = ClassifierService()
    assert not svc.is_available()

    mock_classifier_instance = MagicMock()
    mock_classifier_instance.device = "cpu"
    mock_classifier_instance.classify_clause.return_value = {
        "predicted_category": "Confidentiality",
        "top_predictions": [{"label": "Confidentiality", "confidence": 0.99}],
        "device": "cpu"
    }

    with patch.object(svc, "load_model") as mock_load:
        # Simulate loaded state
        svc._classifier = mock_classifier_instance
        svc._is_loaded = True

        res = svc.classify("This is confidential information.")
        assert res["predicted_category"] == "Confidentiality"
        assert res["top_predictions"][0]["confidence"] == 0.99
        mock_load.assert_not_called()


@pytest.mark.anyio
async def test_analysis_service_ai_mode_integration():
    sample_doc = DocumentDetail(
        id="doc_test123",
        filename="contract.pdf",
        page_count=1,
        word_count=50,
        uploadedAt="2026-10-17T00:00:00Z",
        status="ready",
        demo_mode=False,
        pages=[
            PageText(
                page_number=1,
                text="Confidentiality Agreement. The parties shall hold in confidence all proprietary materials. Neither party shall disclose information."
            )
        ]
    )

    # Mock Ollama output with JSON
    mock_ollama_json = (
        '{"overview": "Mutual non-disclosure agreement protecting proprietary materials.", '
        '"contract_type": "Non-Disclosure Agreement", '
        '"parties": ["Disclosing Party", "Receiving Party"], '
        '"effective_date": "Upon Execution", '
        '"duration": "3 years", '
        '"key_obligations": ["Keep proprietary materials confidential"], '
        '"risks": [{"id": "risk-01", "severity": "low", "title": "Standard NDA", "explanation": "Minimal risk", "impact": "None", "suggestion": "Standard execution"}]}'
    )

    with patch.object(settings, "AI_MODE", "ai"), \
         patch("app.services.analysis_service.classifier_service.classify") as mock_classify, \
         patch("app.services.analysis_service.ollama_client.generate", new_callable=AsyncMock) as mock_generate:

        mock_classify.return_value = {
            "predicted_category": "Confidentiality",
            "top_predictions": [{"label": "Confidentiality", "confidence": 0.99}]
        }
        mock_generate.return_value = mock_ollama_json

        res = await get_document_analysis(sample_doc)
        assert res["document_id"] == "doc_test123"
        assert res["demo_mode"] is False
        assert res["summary"]["contract_type"] == "Non-Disclosure Agreement"
        assert len(res["clauses"]) >= 1
        assert res["clauses"][0]["type"] == "Confidentiality"
        assert len(res["risks"]) == 1
        assert res["risks"][0]["severity"] == "low"


def test_api_analysis_endpoint_demo_fallback():
    # Test through the FastAPI HTTP test client
    # First, mock a document in _documents_store
    from app.api.documents import _documents_store
    doc_id = "doc_mock_demo"
    _documents_store[doc_id] = DocumentDetail(
        id=doc_id,
        filename="test.pdf",
        page_count=1,
        word_count=10,
        uploadedAt="2026-10-17T00:00:00Z",
        status="ready",
        demo_mode=True,
        pages=[PageText(page_number=1, text="Test page content.")]
    )

    with patch.object(settings, "AI_MODE", "demo"):
        res = client.get(f"/api/documents/{doc_id}/analysis")
        assert res.status_code == 200
        data = res.json()
        assert data["document_id"] == doc_id
        assert data["demo_mode"] is True
        assert "summary" in data
        assert "clauses" in data
        assert "risks" in data


def test_segmentation_multiple_clauses_on_one_page():
    p1 = (
        "1. Parties and Services. The Provider shall provide the Services described in Exhibit A to the Client.\n"
        "2. Confidentiality. Both parties agree that confidential information disclosed under this agreement shall remain confidential for five years.\n"
        "3. Payment Obligations. Client shall pay all invoiced amounts within thirty days of receipt of invoice.\n"
        "4. Term and Termination. This agreement commences on the Effective Date and continues until terminated by either party.\n"
        "5. Warranties. Provider warrants that all services will be performed in a professional and workmanlike manner.\n"
        "6. Indemnification. Provider agrees to indemnify Client against third-party claims arising from Provider gross negligence.\n"
        "7. Limitation of Liability. Neither party shall be liable for indirect, incidental, or consequential damages."
    )
    doc = DocumentDetail(
        id="doc_multi",
        filename="contract.pdf",
        page_count=1,
        word_count=100,
        uploadedAt="2026-10-17T00:00:00Z",
        status="ready",
        pages=[PageText(page_number=1, text=p1)]
    )
    clauses = chunk_document_into_candidate_clauses(doc)
    assert len(clauses) == 7
    assert clauses[0]["heading"] == "1. Parties and Services"
    assert clauses[0]["page"] == 1
    assert "Exhibit A" in clauses[0]["text"]

    assert clauses[1]["heading"] == "2. Confidentiality"
    assert clauses[1]["page"] == 1

    assert clauses[2]["heading"] == "3. Payment Obligations"
    assert clauses[6]["heading"] == "7. Limitation of Liability"


def test_segmentation_headings_split_across_lines():
    text = (
        "1. Parties and\n"
        "Services. The Provider shall provide consulting and engineering services.\n"
        "2.\n"
        "Confidentiality: Each party shall safeguard proprietary information.\n"
        "3. Payment\n"
        "Obligations. Fees are due net 30."
    )
    doc = DocumentDetail(
        id="doc_split",
        filename="split_headings.pdf",
        page_count=1,
        word_count=30,
        uploadedAt="2026-10-17T00:00:00Z",
        status="ready",
        pages=[PageText(page_number=1, text=text)]
    )
    clauses = chunk_document_into_candidate_clauses(doc)
    assert len(clauses) == 3
    assert clauses[0]["heading"] in ("1. Parties and", "1. Parties and Services")
    assert "consulting and engineering" in clauses[0]["text"]
    assert clauses[1]["heading"] == "2. Confidentiality"
    assert clauses[2]["heading"] in ("3. Payment", "3. Payment Obligations")


def test_segmentation_text_spanning_pages():
    p1 = (
        "1. Parties and Services. The Provider shall provide the Services described in Exhibit A to the Client,\n"
        "commencing immediately upon signing of this Agreement and continuing throughout the Initial Term,"
    )
    p2 = (
        "including all quarterly maintenance visits and software upgrade support.\n"
        "2. Payment Obligations. Client shall pay all invoices within thirty days of receipt."
    )
    doc = DocumentDetail(
        id="doc_span",
        filename="spanning.pdf",
        page_count=2,
        word_count=50,
        uploadedAt="2026-10-17T00:00:00Z",
        status="ready",
        pages=[PageText(page_number=1, text=p1), PageText(page_number=2, text=p2)]
    )
    clauses = chunk_document_into_candidate_clauses(doc)
    assert len(clauses) == 2
    # Clause 1 started on page 1
    assert clauses[0]["heading"] == "1. Parties and Services"
    assert clauses[0]["page"] == 1
    assert "quarterly maintenance visits" in clauses[0]["text"]

    # Clause 2 started on page 2
    assert clauses[1]["heading"] == "2. Payment Obligations"
    assert clauses[1]["page"] == 2
    assert "thirty days" in clauses[1]["text"]


def test_segmentation_headings_in_middle_of_text():
    raw = (
        "This Agreement is entered into by Alpha and Beta. 1. Confidentiality. Secret material stays confidential. "
        "Neither party shall share it. 2. Governing Law. The laws of Delaware govern this Agreement."
    )
    doc = DocumentDetail(
        id="doc_mid",
        filename="middle.pdf",
        page_count=1,
        word_count=30,
        uploadedAt="2026-10-17T00:00:00Z",
        status="ready",
        pages=[PageText(page_number=1, text=raw)]
    )
    clauses = chunk_document_into_candidate_clauses(doc)
    assert len(clauses) == 2
    assert clauses[0]["heading"] == "1. Confidentiality"
    assert clauses[0]["text"] == "1. Confidentiality. Secret material stays confidential. Neither party shall share it."
    assert clauses[1]["heading"] == "2. Governing Law"
    assert clauses[1]["text"] == "2. Governing Law. The laws of Delaware govern this Agreement."


def test_segmentation_real_pdf_line_delimited_headings():
    """Verify that headings on their own lines (without trailing period/colon) segment cleanly."""
    raw = (
        "1. Parties and Services\n"
        "Client and Provider agree to the following terms.\n"
        "2. Confidentiality\n"
        "Information shall remain confidential.\n"
        "3. Payment Obligations\n"
        "Client shall pay invoices within 30 days.\n"
        "4. Indemnification\n"
        "Provider will defend Client against third-party claims."
    )
    doc = DocumentDetail(
        id="doc_lines",
        filename="lines.pdf",
        page_count=1,
        word_count=40,
        uploadedAt="2026-10-18T00:00:00Z",
        status="ready",
        pages=[PageText(page_number=1, text=raw)]
    )
    clauses = chunk_document_into_candidate_clauses(doc)
    assert len(clauses) == 4
    assert clauses[0]["heading"] == "1. Parties and Services"
    assert "Indemnification" not in clauses[2]["text"]
    assert clauses[2]["heading"] == "3. Payment Obligations"
    assert clauses[3]["heading"] == "4. Indemnification"


@pytest.mark.anyio
async def test_risk_evidence_grounding_verified_and_unverified(monkeypatch):
    """Verify that risk evidence present in document text is marked verified, while missing or truncated excerpts are marked unverified."""
    from app.services.analysis_service import run_ai_document_analysis
    from unittest.mock import AsyncMock

    doc = DocumentDetail(
        id="doc_grounding",
        filename="grounding.pdf",
        page_count=1,
        word_count=50,
        uploadedAt="2026-10-18T00:00:00Z",
        status="ready",
        pages=[PageText(page_number=1, text="1. Payment Obligations\nClient shall pay INR 120,000 within thirty days after receiving each invoice.")]
    )

    mock_ollama_response = {
        "summary": "Sample summary",
        "keyObligations": ["Pay fees"],
        "governingLaw": "Delaware",
        "criticalDeadlines": ["30 days"],
        "risks": [
            {
                "id": "risk-1",
                "clause": "Payment Obligations",
                "severity": "low",
                "issue": "Valid excerpt check",
                "relevantText": "within thirty days",
                "recommendation": "Review terms"
            },
            {
                "id": "risk-2",
                "clause": "Payment Obligations",
                "severity": "high",
                "issue": "Hallucinated excerpt not in text",
                "relevantText": "Client must reimburse travel expenses within 5 days",
                "recommendation": "Fix payment terms"
            },
            {
                "id": "risk-3",
                "clause": "Payment Obligations",
                "severity": "medium",
                "issue": "Short excerpt check",
                "relevantText": "pay",
                "recommendation": "Clarify"
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.generate.return_value = json.dumps(mock_ollama_response)
    monkeypatch.setattr("app.services.analysis_service.ollama_client", mock_client)

    result = await run_ai_document_analysis(doc)
    assert result is not None
    risks = result.get("risks", [])
    assert len(risks) == 3

    assert risks[0]["relevantText"] == "within thirty days"
    assert risks[0]["evidence_unverified"] is False

    assert risks[1]["relevantText"] == "Client must reimburse travel expenses within 5 days"
    assert risks[1]["evidence_unverified"] is True

    assert risks[2]["relevantText"] == "pay"
    assert risks[2]["evidence_unverified"] is True


