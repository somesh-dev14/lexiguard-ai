"""
Regression test: verifies clause segmentation against the actual LexiGuard AI
sample contract text (8-clause, 2-page commercial agreement).

Page 1 - clauses 1-7
Page 2 - clause 8: Notices and Amendments
"""

import pytest
from unittest.mock import patch, AsyncMock

from app.services.analysis_service import (
    chunk_document_into_candidate_clauses,
    run_ai_document_analysis,
)
from app.schemas.document import DocumentDetail, PageText
from app.core.config import settings

PAGE_1_TEXT = (
    "SERVICE AGREEMENT\n\n"
    "This Service Agreement (Agreement) is entered into as of January 1, 2025,\n"
    "by and between Alpha Technologies Inc. (Provider) and Beta Corp. (Client).\n\n"
    "1. Parties and Services. Provider agrees to deliver software development and\n"
    "consulting services as described in Exhibit A attached hereto. Provider shall\n"
    "assign qualified personnel to perform all services in a professional manner.\n\n"
    "2. Confidentiality. Each party agrees to hold in strict confidence all\n"
    "Proprietary Information disclosed by the other party and shall not disclose\n"
    "such information to any third party without prior written consent. This\n"
    "obligation survives termination for a period of five (5) years.\n\n"
    "3. Payment Obligations. Client shall pay all invoiced amounts within thirty\n"
    "(30) days of receipt of invoice. Invoices not paid within sixty (60) days\n"
    "shall accrue interest at the rate of 1.5% per month.\n\n"
    "4. Indemnification. Provider agrees to defend, indemnify, and hold harmless\n"
    "Client from and against any and all third-party claims, damages, losses, and\n"
    "expenses arising out of Provider gross negligence or willful misconduct.\n\n"
    "5. Termination. Either party may terminate this Agreement upon thirty (30)\n"
    "days written notice. Upon termination, all outstanding invoices become\n"
    "immediately due and payable.\n\n"
    "6. Governing Law. This Agreement shall be governed by and construed in\n"
    "accordance with the laws of the State of Delaware, without regard to its\n"
    "conflict of law provisions.\n\n"
    "7. Limitation of Liability. In no event shall either party be liable for\n"
    "any indirect, incidental, special, exemplary, or consequential damages.\n"
    "Each party aggregate liability shall not exceed the total fees paid in the\n"
    "prior twelve (12) months.\n"
)

PAGE_2_TEXT = (
    "8. Notices and Amendments. All notices required or permitted hereunder shall\n"
    "be in writing and delivered by certified mail, email with read receipt, or\n"
    "overnight courier. This Agreement may be amended only by a written\n"
    "instrument signed by authorised representatives of both parties.\n\n"
    "IN WITNESS WHEREOF, the parties have executed this Agreement as of the date\n"
    "first written above.\n"
)

EXPECTED_HEADINGS = [
    "1. Parties and Services",
    "2. Confidentiality",
    "3. Payment Obligations",
    "4. Indemnification",
    "5. Termination",
    "6. Governing Law",
    "7. Limitation of Liability",
    "8. Notices and Amendments",
]

EXPECTED_PAGE = {
    "1. Parties and Services": 1,
    "2. Confidentiality": 1,
    "3. Payment Obligations": 1,
    "4. Indemnification": 1,
    "5. Termination": 1,
    "6. Governing Law": 1,
    "7. Limitation of Liability": 1,
    "8. Notices and Amendments": 2,
}

CLAUSE_CONTENT_SNIPPETS = {
    "1. Parties and Services": "Exhibit A",
    "2. Confidentiality": "five (5) years",
    "3. Payment Obligations": "thirty",
    "4. Indemnification": "indemnify",
    "5. Termination": "thirty (30)",
    "6. Governing Law": "Delaware",
    "7. Limitation of Liability": "aggregate liability",
    "8. Notices and Amendments": "certified mail",
}

CLAUSE_EXCLUSION_SNIPPETS = {
    "1. Parties and Services": ["five (5) years", "certified mail"],
    "8. Notices and Amendments": ["Exhibit A", "aggregate liability"],
}


def make_sample_doc():
    return DocumentDetail(
        id="doc_sample_contract",
        filename="sample_contract.pdf",
        page_count=2,
        word_count=400,
        uploadedAt="2026-01-01T00:00:00Z",
        status="ready",
        demo_mode=False,
        pages=[
            PageText(page_number=1, text=PAGE_1_TEXT),
            PageText(page_number=2, text=PAGE_2_TEXT),
        ],
    )


def test_sample_contract_exactly_eight_clauses():
    doc = make_sample_doc()
    clauses = chunk_document_into_candidate_clauses(doc)
    headings = [c["heading"] for c in clauses]
    assert len(clauses) == 8, f"Expected 8 clauses, got {len(clauses)}. Found: {headings}"


def test_sample_contract_correct_headings():
    doc = make_sample_doc()
    clauses = chunk_document_into_candidate_clauses(doc)
    actual = [c["heading"] for c in clauses]
    assert actual == EXPECTED_HEADINGS, f"Expected:\n{EXPECTED_HEADINGS}\nGot:\n{actual}"


def test_sample_contract_correct_page_numbers():
    doc = make_sample_doc()
    clauses = chunk_document_into_candidate_clauses(doc)
    for c in clauses:
        expected = EXPECTED_PAGE[c["heading"]]
        assert c["page"] == expected, (
            f"Clause '{c['heading']}': expected page {expected}, got {c['page']}"
        )


def test_sample_contract_clause_content_not_mixed():
    doc = make_sample_doc()
    clauses = chunk_document_into_candidate_clauses(doc)
    heading_to_clause = {c["heading"]: c for c in clauses}

    for heading, snippet in CLAUSE_CONTENT_SNIPPETS.items():
        clause = heading_to_clause[heading]
        assert snippet in clause["text"], (
            f"Clause '{heading}' missing snippet '{snippet}'. Text: {clause['text'][:200]}"
        )

    for heading, excluded in CLAUSE_EXCLUSION_SNIPPETS.items():
        clause = heading_to_clause[heading]
        for snip in excluded:
            assert snip not in clause["text"], (
                f"Clause '{heading}' incorrectly contains '{snip}'"
            )


def test_sample_contract_clause_ids_sequential():
    doc = make_sample_doc()
    clauses = chunk_document_into_candidate_clauses(doc)
    for i, c in enumerate(clauses, start=1):
        assert c["id"] == f"clause-{i:02d}", f"Expected 'clause-{i:02d}', got '{c['id']}'"


MOCK_OLLAMA_JSON = (
    '{"overview": "Two-party service agreement between Alpha Technologies and Beta Corp.", '
    '"contract_type": "Service Agreement", '
    '"parties": ["Alpha Technologies Inc.", "Beta Corp."], '
    '"effective_date": "January 1, 2025", '
    '"duration": "Until terminated", '
    '"key_obligations": ["Deliver software services", "Maintain confidentiality", "Pay invoices within 30 days"], '
    '"risks": [{"id": "risk-01", "severity": "medium", "title": "Liability Cap", '
    '"explanation": "Liability limited to prior 12 months fees.", "impact": "Limited recovery", '
    '"suggestion": "Negotiate higher cap"}]}'
)

CLASSIFIER_CATEGORY_ORDER = [
    "Parties", "Confidentiality", "Payment Terms", "Indemnification",
    "Termination", "Governing Law", "Limitation of Liability", "Notices",
]


@pytest.mark.anyio
async def test_sample_contract_full_ai_analysis():
    doc = make_sample_doc()
    call_count = [0]

    def mock_classify(text, top_k=3):
        idx = min(call_count[0], len(CLASSIFIER_CATEGORY_ORDER) - 1)
        cat = CLASSIFIER_CATEGORY_ORDER[idx]
        call_count[0] += 1
        return {
            "predicted_category": cat,
            "top_predictions": [{"label": cat, "confidence": 0.9}],
        }

    with patch.object(settings, "AI_MODE", "ai"), \
         patch("app.services.analysis_service.classifier_service.classify", side_effect=mock_classify), \
         patch("app.services.analysis_service.ollama_client.generate",
               new_callable=AsyncMock, return_value=MOCK_OLLAMA_JSON):

        result = await run_ai_document_analysis(doc)

    assert result["document_id"] == "doc_sample_contract"
    assert result["demo_mode"] is False

    clauses = result["clauses"]
    assert len(clauses) == 8, f"Expected 8 clauses in analysis, got {len(clauses)}"

    summary = result["summary"]
    assert summary["contract_type"] == "Service Agreement"
    assert "January 1, 2025" in summary["effective_date"]

    risks = result["risks"]
    assert len(risks) >= 1
    assert risks[0]["severity"] in ("low", "medium", "high")
    assert risks[0]["demo"] is False


def test_clause_page_span_entirely_on_one_page():
    """Test a clause that begins and ends strictly within Page 1."""
    doc = DocumentDetail(
        id="doc_single_page",
        filename="single_page.pdf",
        page_count=2,
        word_count=100,
        uploadedAt="2026-01-01T00:00:00Z",
        status="ready",
        pages=[
            PageText(page_number=1, text="1. Confidentiality.\nAll confidential information must remain secret.\n\n2. Governing Law.\nLaws of Delaware."),
            PageText(page_number=2, text="3. Notices.\nDelivered by courier."),
        ],
    )
    clauses = chunk_document_into_candidate_clauses(doc)
    assert len(clauses) == 3

    c1 = clauses[0]
    assert c1["heading"] == "1. Confidentiality"
    assert c1["page"] == 1
    assert c1["page_start"] == 1
    assert c1["page_end"] == 1
    assert c1["page_span"] == "1"


def test_clause_page_span_beginning_on_page_1_and_ending_on_page_2():
    """Test a multi-page clause that starts on Page 1 and continues onto Page 2."""
    doc = DocumentDetail(
        id="doc_multi_page",
        filename="multi_page.pdf",
        page_count=3,
        word_count=150,
        uploadedAt="2026-01-01T00:00:00Z",
        status="ready",
        pages=[
            PageText(page_number=1, text="1. Term and Scope.\nThis clause begins on page 1 and defines the services to be provided across multiple phases."),
            PageText(page_number=2, text="The services continue into phase two and phase three as detailed herein.\n\n2. Miscellaneous.\nThis is section two on page 2."),
            PageText(page_number=3, text="3. Execution.\nSigned by both parties."),
        ],
    )
    clauses = chunk_document_into_candidate_clauses(doc)
    assert len(clauses) == 3

    # Clause 1 begins on page 1 and ends before Clause 2 on page 2
    c1 = clauses[0]
    assert c1["heading"] == "1. Term and Scope"
    assert c1["page"] == 1
    assert c1["page_start"] == 1
    assert c1["page_end"] == 2
    assert c1["page_span"] == "1-2"

    # Clause 2 begins and ends on page 2
    c2 = clauses[1]
    assert c2["heading"] == "2. Miscellaneous"
    assert c2["page"] == 2
    assert c2["page_start"] == 2
    assert c2["page_end"] == 2
    assert c2["page_span"] == "2"


def test_clause_page_span_ending_exactly_at_page_boundary():
    """Test a clause that occupies the entirety of Page 1 up to its exact last character."""
    page1_text = "1. Entire Agreement.\nThis agreement constitutes the complete understanding between the parties."
    doc = DocumentDetail(
        id="doc_boundary",
        filename="boundary.pdf",
        page_count=2,
        word_count=50,
        uploadedAt="2026-01-01T00:00:00Z",
        status="ready",
        pages=[
            PageText(page_number=1, text=page1_text),
            PageText(page_number=2, text="2. Signatures.\nAuthorized signatures appear below."),
        ],
    )
    clauses = chunk_document_into_candidate_clauses(doc)
    assert len(clauses) == 2

    # Clause 1 ends before clause 2 starts on page 2, so its text is entirely on page 1
    c1 = clauses[0]
    assert c1["heading"] == "1. Entire Agreement"
    assert c1["page"] == 1
    assert c1["page_start"] == 1
    assert c1["page_end"] == 1
    assert c1["page_span"] == "1"

    c2 = clauses[1]
    assert c2["heading"] == "2. Signatures"
    assert c2["page"] == 2
    assert c2["page_start"] == 2
    assert c2["page_end"] == 2
    assert c2["page_span"] == "2"


def test_clause_page_span_empty_and_boundary_safe_inputs():
    """Test boundary safety with empty pages, whitespace-only pages, and fallback paragraphs."""
    # Empty doc
    empty_doc = DocumentDetail(
        id="doc_empty", filename="empty.pdf", page_count=0,
        word_count=0, uploadedAt="", status="ready", pages=[]
    )
    assert chunk_document_into_candidate_clauses(empty_doc) == []

    # Whitespace only
    ws_doc = DocumentDetail(
        id="doc_ws", filename="ws.pdf", page_count=1,
        word_count=0, uploadedAt="", status="ready",
        pages=[PageText(page_number=1, text="   \n\n   \t  ")]
    )
    assert chunk_document_into_candidate_clauses(ws_doc) == []

    # Paragraph fallback with unnumbered text spanning paragraph
    para_doc = DocumentDetail(
        id="doc_para", filename="para.pdf", page_count=2,
        word_count=60, uploadedAt="", status="ready",
        pages=[
            PageText(page_number=1, text="The Provider agrees to maintain operational reliability for all customer services and guarantees ninety-nine percent uptime throughout the contract term.\n\nCustomer shall review monthly performance logs."),
            PageText(page_number=2, text="All dispute resolution procedures will be administered under the rules of arbitration in the State of Delaware."),
        ]
    )
    para_clauses = chunk_document_into_candidate_clauses(para_doc)
    assert len(para_clauses) >= 1
    for pc in para_clauses:
        assert pc["page"] == pc["page_start"] == pc["page_end"]
        assert pc["page_span"] == str(pc["page"])
