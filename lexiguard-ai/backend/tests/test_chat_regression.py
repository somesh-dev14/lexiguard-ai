"""
Regression tests for the chat Q&A workflow:
- Document context isolation (only queries the specified document)
- Payment question retrieval from the correct clause
- Citation page validation (cannot cite nonexistent pages)
- Evidence grounding (excerpts must come from document text)
- Error surfacing (no fabricated answers on failure)
- Demo mode badge accuracy
"""

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.schemas.document import DocumentDetail, PageText
from app.services.chat_service import (
    answer_document_question,
    _build_page_context,
    _find_relevant_pages,
    _validate_page_citations,
    _sanitize_chat_answer,
    _deduplicate_citations,
)
from app.core.config import settings


# -- Fixtures: Two-page sample contract matching lexiguard_sample_contract.pdf --

SAMPLE_PAGE_1 = (
    "SERVICE AGREEMENT\n\n"
    "This Service Agreement (Agreement) is entered into as of January 1, 2025,\n"
    "by and between Alpha Technologies Inc. (Provider) and Beta Corp. (Client).\n\n"
    "1. Parties and Services. Provider agrees to deliver software development and\n"
    "consulting services as described in Exhibit A attached hereto.\n\n"
    "2. Confidentiality. Each party agrees to hold in strict confidence all\n"
    "Proprietary Information disclosed by the other party.\n\n"
    "3. Payment Obligations. Client shall pay Provider the sum of INR 120,000\n"
    "(Indian Rupees One Lakh Twenty Thousand) within thirty (30) days of receipt\n"
    "of a valid invoice. Overdue undisputed amounts shall accrue interest at the\n"
    "rate of 1% per month, subject to applicable law. All invoices must include\n"
    "a description of services rendered and the applicable purchase order number.\n"
    "Client may dispute an invoice in writing within fifteen (15) days of receipt.\n\n"
    "4. Indemnification. Provider agrees to defend, indemnify, and hold harmless\n"
    "Client from third-party claims arising from Provider gross negligence.\n\n"
    "5. Termination. Either party may terminate this Agreement upon thirty (30)\n"
    "days written notice.\n\n"
    "6. Governing Law. This Agreement shall be governed by the laws of the\n"
    "State of Delaware.\n\n"
    "7. Limitation of Liability. In no event shall either party be liable for\n"
    "any indirect, incidental, special, or consequential damages."
)

SAMPLE_PAGE_2 = (
    "8. Notices and Amendments. All notices required hereunder shall be in\n"
    "writing and delivered by certified mail or email with read receipt.\n\n"
    "IN WITNESS WHEREOF, the parties have executed this Agreement as of the\n"
    "date first written above."
)


def make_sample_doc(doc_id="doc_sample_contract"):
    return DocumentDetail(
        id=doc_id,
        filename="lexiguard_sample_contract.pdf",
        page_count=2,
        word_count=300,
        uploadedAt="2026-01-01T00:00:00Z",
        status="ready",
        demo_mode=False,
        pages=[
            PageText(page_number=1, text=SAMPLE_PAGE_1),
            PageText(page_number=2, text=SAMPLE_PAGE_2),
        ],
    )


def make_other_doc():
    """A different document — should never leak into sample contract queries."""
    return DocumentDetail(
        id="doc_other_contract",
        filename="other_contract.pdf",
        page_count=1,
        word_count=50,
        uploadedAt="2026-01-01T00:00:00Z",
        status="ready",
        demo_mode=False,
        pages=[
            PageText(
                page_number=1,
                text="1. Non-Compete. Employee shall not compete for 24 months.",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Context Building Tests
# ---------------------------------------------------------------------------


class TestBuildPageContext:
    def test_includes_all_pages(self):
        doc = make_sample_doc()
        ctx = _build_page_context(doc)
        assert "--- Page 1 ---" in ctx
        assert "--- Page 2 ---" in ctx
        assert "INR 120,000" in ctx
        assert "Notices and Amendments" in ctx

    def test_empty_pages(self):
        doc = DocumentDetail(
            id="doc_empty", filename="empty.pdf", page_count=0,
            word_count=0, uploadedAt="", status="ready", pages=[]
        )
        assert _build_page_context(doc) == ""


# ---------------------------------------------------------------------------
# Relevance Scoring Tests
# ---------------------------------------------------------------------------


class TestFindRelevantPages:
    def test_payment_question_scores_page1_highest(self):
        doc = make_sample_doc()
        pages = _find_relevant_pages(doc, "What are the payment terms and penalties for late payment?")
        assert len(pages) >= 1
        # Page 1 should score highest because it contains the Payment Obligations clause
        assert pages[0]["page_number"] == 1

    def test_notices_question_scores_page2_highest(self):
        doc = make_sample_doc()
        pages = _find_relevant_pages(doc, "How should notices be delivered?")
        assert len(pages) >= 1
        # Page 2 has the Notices clause
        assert pages[0]["page_number"] == 2


# ---------------------------------------------------------------------------
# Citation Validation Tests
# ---------------------------------------------------------------------------


class TestValidatePageCitations:
    def test_valid_citation_passes(self):
        doc = make_sample_doc()
        sources = [{"page": 1, "excerpt": "INR 120,000"}]
        result = _validate_page_citations(sources, doc)
        assert len(result) == 1
        assert result[0]["excerpt_verified"] is True

    def test_nonexistent_page_dropped(self):
        doc = make_sample_doc()
        sources = [
            {"page": 1, "excerpt": "INR 120,000"},
            {"page": 4, "excerpt": "This page does not exist"},
            {"page": 99, "excerpt": "Neither does this"},
        ]
        result = _validate_page_citations(sources, doc)
        assert len(result) == 1
        assert result[0]["page"] == 1

    def test_wrong_page_corrected(self):
        """If excerpt is on page 1 but cited as page 2, it gets corrected."""
        doc = make_sample_doc()
        sources = [{"page": 2, "excerpt": "INR 120,000"}]
        result = _validate_page_citations(sources, doc)
        assert len(result) == 1
        assert result[0]["page"] == 1  # corrected from 2 to 1

    def test_short_excerpt_marked_unverified(self):
        doc = make_sample_doc()
        sources = [{"page": 1, "excerpt": "pay"}]
        result = _validate_page_citations(sources, doc)
        assert len(result) == 1
        assert result[0]["excerpt_verified"] is False


# ---------------------------------------------------------------------------
# Document Context Isolation Tests
# ---------------------------------------------------------------------------


class TestDocumentIsolation:
    @pytest.mark.anyio
    async def test_chat_uses_only_specified_document(self):
        """The prompt sent to Ollama must contain text from doc_sample_contract only."""
        doc = make_sample_doc()
        other_doc = make_other_doc()

        captured_prompts = []

        async def mock_generate(prompt, system_prompt=None, **kwargs):
            captured_prompts.append(prompt)
            return json.dumps({
                "answer": "Payment is INR 120,000 within 30 days.",
                "sources": [{"page": 1, "excerpt": "INR 120,000"}],
            })

        with patch("app.services.chat_service.ollama_client.generate", side_effect=mock_generate):
            result = await answer_document_question(doc, "What are the payment terms?")

        assert len(captured_prompts) == 1
        prompt_text = captured_prompts[0]

        # Must contain content from the sample document
        assert "INR 120,000" in prompt_text
        assert "Payment Obligations" in prompt_text

        # Must NOT contain content from the other document
        assert "Non-Compete" not in prompt_text
        assert "24 months" not in prompt_text  # other doc's non-compete duration

    @pytest.mark.anyio
    async def test_chat_does_not_leak_between_documents(self):
        """Two sequential calls to different documents should not share context."""
        doc1 = make_sample_doc("doc_1")
        doc2 = make_other_doc()

        captured_prompts = []

        async def mock_generate(prompt, system_prompt=None, **kwargs):
            captured_prompts.append(prompt)
            return json.dumps({"answer": "Test answer.", "sources": []})

        with patch("app.services.chat_service.ollama_client.generate", side_effect=mock_generate):
            await answer_document_question(doc1, "What are the payment terms?")
            await answer_document_question(doc2, "What is the non-compete clause?")

        assert len(captured_prompts) == 2
        # First call should have doc1 content, not doc2
        assert "INR 120,000" in captured_prompts[0]
        assert "Non-Compete" not in captured_prompts[0]
        # Second call should have doc2 content, not doc1
        assert "Non-Compete" in captured_prompts[1]
        assert "INR 120,000" not in captured_prompts[1]


# ---------------------------------------------------------------------------
# Payment Question Regression Test
# ---------------------------------------------------------------------------


class TestPaymentQuestionRegression:
    @pytest.mark.anyio
    async def test_payment_question_retrieves_payment_clause(self):
        """
        Regression test: the exact question 'What are the payment terms and penalties
        for late payment?' must retrieve the Payment Obligations clause from the
        sample contract and the answer must reference INR 120,000 and 30 days.
        """
        doc = make_sample_doc()

        mock_response = json.dumps({
            "answer": (
                "According to Section 3 (Payment Obligations), the Client shall pay "
                "INR 120,000 within thirty (30) days of receipt of a valid invoice. "
                "Overdue undisputed amounts accrue interest at 1% per month, subject to "
                "applicable law. The Client may dispute an invoice in writing within "
                "fifteen (15) days of receipt."
            ),
            "sources": [
                {"page": 1, "excerpt": "Client shall pay Provider the sum of INR 120,000"},
                {"page": 1, "excerpt": "Overdue undisputed amounts shall accrue interest at the rate of 1% per month"},
            ],
        })

        with patch(
            "app.services.chat_service.ollama_client.generate",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await answer_document_question(
                doc, "What are the payment terms and penalties for late payment?"
            )

        assert result["demo_mode"] is False
        answer = result["answer"]
        # The answer must reference key payment details from the document
        assert "INR 120,000" in answer or "120,000" in answer
        assert "30" in answer or "thirty" in answer.lower()

        # All cited pages must be valid (1 or 2 for this 2-page doc)
        for src in result["sources"]:
            assert 1 <= src["page"] <= 2, f"Invalid page citation: {src['page']}"

    @pytest.mark.anyio
    async def test_payment_question_context_includes_payment_clause(self):
        """The prompt sent to Ollama must include the Payment Obligations text."""
        doc = make_sample_doc()

        captured_prompts = []

        async def capture_generate(prompt, system_prompt=None, **kwargs):
            captured_prompts.append(prompt)
            return json.dumps({"answer": "Test", "sources": []})

        with patch("app.services.chat_service.ollama_client.generate", side_effect=capture_generate):
            await answer_document_question(
                doc, "What are the payment terms and penalties for late payment?"
            )

        prompt = captured_prompts[0]
        # The document context must include the payment clause
        assert "INR 120,000" in prompt
        assert "1% per month" in prompt
        assert "fifteen (15) days" in prompt


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


class TestChatErrorHandling:
    @pytest.mark.anyio
    async def test_ollama_failure_raises_runtime_error(self):
        """When Ollama fails, the service must raise an error, not return demo data."""
        doc = make_sample_doc()

        with patch(
            "app.services.chat_service.ollama_client.generate",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Connection refused"),
        ):
            with pytest.raises(RuntimeError, match="Connection refused"):
                await answer_document_question(doc, "What are the payment terms?")

    @pytest.mark.anyio
    async def test_ollama_timeout_raises_timeout_error(self):
        """Timeout errors must propagate without being swallowed."""
        doc = make_sample_doc()

        with patch(
            "app.services.chat_service.ollama_client.generate",
            new_callable=AsyncMock,
            side_effect=TimeoutError("Ollama timed out after 120s"),
        ):
            with pytest.raises(TimeoutError, match="timed out"):
                await answer_document_question(doc, "What are the payment terms?")

    @pytest.mark.anyio
    async def test_empty_document_returns_error(self):
        """A document with no extracted text should return a descriptive error."""
        doc = DocumentDetail(
            id="doc_empty", filename="empty.pdf", page_count=0,
            word_count=0, uploadedAt="", status="ready",
            pages=[],
        )
        result = await answer_document_question(doc, "What are the terms?")
        assert result.get("error") is True
        assert "No text" in result["answer"]


# ---------------------------------------------------------------------------
# API Endpoint Integration Tests
# ---------------------------------------------------------------------------


class TestChatAPIEndpoint:
    def test_chat_endpoint_returns_answer(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.api.documents import _documents_store

        client = TestClient(app)
        doc = make_sample_doc("doc_chat_test")
        _documents_store["doc_chat_test"] = doc

        mock_response = json.dumps({
            "answer": "Payment is INR 120,000 within 30 days.",
            "sources": [{"page": 1, "excerpt": "INR 120,000"}],
        })

        with patch(
            "app.services.chat_service.ollama_client.generate",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            res = client.post(
                "/api/documents/doc_chat_test/chat",
                json={"question": "What are the payment terms?"},
            )

        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert data["demo_mode"] is False
        assert isinstance(data["sources"], list)

        # Cleanup
        del _documents_store["doc_chat_test"]

    def test_chat_endpoint_missing_document_returns_404(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        res = client.post(
            "/api/documents/doc_nonexistent/chat",
            json={"question": "Hello?"},
        )
        assert res.status_code == 404

    def test_chat_endpoint_empty_question_returns_400(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.api.documents import _documents_store

        doc = make_sample_doc("doc_empty_q")
        _documents_store["doc_empty_q"] = doc

        client = TestClient(app)
        res = client.post(
            "/api/documents/doc_empty_q/chat",
            json={"question": ""},
        )
        assert res.status_code == 400

        # Cleanup
        del _documents_store["doc_empty_q"]

    def test_chat_endpoint_ollama_failure_returns_500(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.api.documents import _documents_store

        doc = make_sample_doc("doc_fail_test")
        _documents_store["doc_fail_test"] = doc

        client = TestClient(app)

        with patch(
            "app.services.chat_service.ollama_client.generate",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Ollama crashed"),
        ):
            res = client.post(
                "/api/documents/doc_fail_test/chat",
                json={"question": "What are the terms?"},
            )

        assert res.status_code == 500
        data = res.json()
        assert "detail" in data

        # Cleanup
        del _documents_store["doc_fail_test"]


# ---------------------------------------------------------------------------
# Valid Page Number Tests
# ---------------------------------------------------------------------------


class TestValidPageNumbers:
    @pytest.mark.anyio
    async def test_citations_cannot_exceed_document_page_count(self):
        """Even if Ollama cites page 4, it must be dropped for a 2-page document."""
        doc = make_sample_doc()

        mock_response = json.dumps({
            "answer": "The liability cap is discussed.",
            "sources": [
                {"page": 1, "excerpt": "INR 120,000"},
                {"page": 4, "excerpt": "This page does not exist"},
                {"page": 2, "excerpt": "certified mail"},
            ],
        })

        with patch(
            "app.services.chat_service.ollama_client.generate",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await answer_document_question(doc, "What is the liability cap?")

        # Page 4 must be removed; only pages 1 and 2 are valid
        for src in result["sources"]:
            assert src["page"] in (1, 2), f"Invalid page citation: {src['page']}"

        # Total sources should be 2 (page 4 dropped)
        assert len(result["sources"]) == 2


# ---------------------------------------------------------------------------
# Chat Response Quality & Anti-Repetition Regression Tests
# ---------------------------------------------------------------------------


class TestChatResponseQuality:
    def test_sanitize_chat_answer_strips_thinking_and_meta_narration(self):
        dirty = (
            "<think>Analyzing clause 3 for payment details.</think>\n"
            "Now we need to extract the exact quote.\n"
            "Here is the direct answer:\n"
            "- Client must pay INR 120,000 within 30 days of invoice.\n"
            "- Overdue interest accrues at 1% per month.\n"
            "We should also check if the"
        )
        cleaned = _sanitize_chat_answer(dirty)
        assert "<think>" not in cleaned
        assert "</think>" not in cleaned
        assert "Now we need to extract" not in cleaned
        assert "Here is the direct answer" not in cleaned
        assert "We should also check if the" not in cleaned  # trailing incomplete clause dropped
        assert "INR 120,000" in cleaned
        assert "1% per month" in cleaned

    def test_deduplicate_citations_eliminates_redundancy(self):
        duplicate_sources = [
            {"page": 1, "excerpt": "Client shall pay Provider the sum of INR 120,000 within thirty days"},
            {"page": 1, "excerpt": "Client shall pay Provider the sum of INR 120,000 within thirty days"},
            {"page": 1, "excerpt": "Overdue undisputed amounts shall accrue interest at 1% per month"},
        ]
        deduped = _deduplicate_citations(duplicate_sources)
        assert len(deduped) == 2
        assert deduped[0]["excerpt"] != deduped[1]["excerpt"]

    @pytest.mark.anyio
    async def test_unsupported_question_explicitly_discloses_absence(self):
        doc = make_sample_doc()
        mock_response = json.dumps({
            "answer": "The provided document does not contain information regarding healthcare benefits or dental insurance.",
            "sources": [],
        })
        with patch("app.services.chat_service.ollama_client.generate",
                   new_callable=AsyncMock, return_value=mock_response):
            result = await answer_document_question(doc, "What dental insurance benefits are provided?")

        assert "does not contain" in result["answer"].lower()
        assert len(result["sources"]) == 0

    @pytest.mark.anyio
    async def test_truncated_json_model_response_is_repaired(self):
        doc = make_sample_doc()
        # Truncated JSON without closing brackets
        truncated_json = '{"answer": "- Fee: INR 120,000\\n- Late interest: 1% monthly", "sources": [{"page": 1, "excerpt": "INR 120,000"}'

        with patch("app.services.chat_service.ollama_client.generate",
                   new_callable=AsyncMock, return_value=truncated_json):
            result = await answer_document_question(doc, "What are the payment terms?")

        assert "INR 120,000" in result["answer"]
        assert len(result["sources"]) == 1
        assert result["sources"][0]["page"] == 1
