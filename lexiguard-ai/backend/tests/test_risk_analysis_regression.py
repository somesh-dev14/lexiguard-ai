"""
Regression tests for Risk Analysis module:
1. Verifies that the sample contract (lexiguard_sample_contract.pdf) does not receive a HIGH
   "Incomplete payment terms" finding solely because of truncated evidence ("Client sha").
2. The complete payment clause (INR 120,000, 30 days, 1% interest, 15 days dispute) is retained
   and correctly attributed to page 1.
3. A genuinely missing payment deadline can still be flagged when supported by the contract text.
4. Unsupported, truncated, or unrelated evidence is marked unverified and not displayed as verified.
5. Evidence grounding maps to the correct source clause and page.
"""

import json
import pytest
from unittest.mock import patch, AsyncMock

from app.services.analysis_service import (
    chunk_document_into_candidate_clauses,
    run_ai_document_analysis,
)
from app.schemas.document import DocumentDetail, PageText
from app.core.config import settings


SAMPLE_CONTRACT_PAGE_1 = (
    "LexiGuard AI test document - Fictional\n"
    "Page 1\n"
    "SAMPLE SERVICES AGREEMENT\n"
    "Fictional test document for LexiGuard AI - not legal advice or a real contract\n\n"
    "1. Parties and Services\n"
    "This Services Agreement (the 'Agreement') is entered into on 1 October 2026 by Example Client Ltd. ('Client') and "
    "Sample Solutions Pvt. Ltd. ('Provider'). Provider will provide software implementation and technical support services "
    "described in mutually agreed written statements of work.\n\n"
    "2. Confidentiality\n"
    "Each party shall protect all non-public business, technical, financial, and customer information received from the other "
    "party ('Confidential Information'). Neither party may disclose Confidential Information to a third party without prior "
    "written consent. These obligations continue for three years after termination.\n\n"
    "3. Payment Obligations\n"
    "Client shall pay Provider a service fee of INR 120,000 within thirty days after receiving each valid invoice. Overdue "
    "undisputed amounts may accrue interest at 1% per month, subject to applicable law. Provider must describe the "
    "services and applicable taxes on each invoice. Client may dispute an invoice in good faith by giving written notice "
    "within fifteen days.\n\n"
    "4. Indemnification\n"
    "Provider shall indemnify and defend Client against third-party claims, damages, and reasonable legal expenses to the "
    "extent arising directly from Provider's infringement of a third party's intellectual property rights or Provider's willful "
    "misconduct.\n\n"
    "5. Termination\n"
    "Either party may terminate this Agreement for a material breach if the breaching party fails to cure the breach within "
    "thirty days after receiving written notice.\n\n"
    "6. Governing Law\n"
    "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware.\n\n"
    "7. Limitation of Liability\n"
    "Except for payment obligations, confidentiality breaches, indemnification obligations, and liability that cannot legally be "
    "limited, neither party's aggregate liability arising from this Agreement shall exceed the fees paid or payable during the "
    "twelve months preceding the event giving rise to the claim. Neither party shall be liable for indirect or consequential\n"
)

SAMPLE_CONTRACT_PAGE_2 = (
    "LexiGuard AI test document - Fictional\n"
    "Page 2\n"
    "losses to the maximum extent permitted by applicable law.\n"
    "8. Notices and Amendments\n"
    "Formal notices must be sent by email and by tracked courier to the contact details designated by each party in writing. "
    "Any amendment to this Agreement must be in writing and signed by authorized representatives of both parties.\n"
)


def make_sample_contract_doc():
    return DocumentDetail(
        id="doc_sample_contract_test",
        filename="lexiguard_sample_contract.pdf",
        uploadedAt="2026-10-18T00:00:00Z",
        status="ready",
        page_count=2,
        word_count=450,
        pages=[
            PageText(page_number=1, text=SAMPLE_CONTRACT_PAGE_1),
            PageText(page_number=2, text=SAMPLE_CONTRACT_PAGE_2),
        ],
    )


@pytest.mark.anyio
async def test_complete_payment_clause_retained_and_attributed_to_page_1():
    """Verify that the complete payment clause is extracted, not truncated, and attributed to page 1."""
    doc = make_sample_contract_doc()
    clauses = chunk_document_into_candidate_clauses(doc)

    payment_clause = next((c for c in clauses if "Payment" in c["heading"]), None)
    assert payment_clause is not None, "Payment Obligations clause must be extracted"
    assert payment_clause["page"] == 1, "Payment Obligations must be on page 1"

    text = payment_clause["text"]
    # Verify all four key payment terms are present in the segmented clause
    assert "INR 120,000" in text or "120,000" in text
    assert "thirty days" in text
    assert "1% per month" in text
    assert "fifteen days" in text


@pytest.mark.anyio
async def test_no_high_incomplete_payment_terms_from_truncated_evidence():
    """Verify that a model response attempting to cite truncated 'Client sha' is marked unverified."""
    doc = make_sample_contract_doc()

    # Simulated Ollama response that attempts to flag incomplete payment terms with truncated 'Client sha'
    mock_model_response = {
        "overview": "Overview of services agreement",
        "contract_type": "Services Agreement",
        "parties": ["Example Client Ltd.", "Sample Solutions Pvt. Ltd."],
        "effective_date": "1 October 2026",
        "duration": "Unspecified",
        "key_obligations": ["Provide services", "Pay INR 120,000 within 30 days"],
        "risks": [
            {
                "id": "risk-01",
                "severity": "high",
                "title": "Incomplete payment terms",
                "clause": "3. Payment Obligations",
                "explanation": "The Payment Obligations section cuts off mid-sentence.",
                "relevantText": "Client sha",
                "impact": "Unclear payment obligations",
                "suggestion": "Complete the payment terms",
            },
            {
                "id": "risk-02",
                "severity": "medium",
                "title": "Invoice dispute window",
                "clause": "3. Payment Obligations",
                "explanation": "Dispute notice is restricted to fifteen days.",
                "relevantText": "Client may dispute an invoice in good faith by giving written notice within fifteen days.",
                "impact": "Brief window to dispute",
                "suggestion": "Extend dispute window to 30 days",
            }
        ]
    }

    with patch("app.services.analysis_service.ollama_client.generate",
               new_callable=AsyncMock, return_value=json.dumps(mock_model_response)):
        res = await run_ai_document_analysis(doc)

    risks = res["risks"]
    assert len(risks) == 2

    # Truncated evidence "Client sha" must be flagged as unverified (< 15 characters)
    risk1 = risks[0]
    assert risk1["title"] == "Incomplete payment terms"
    assert risk1["evidence_unverified"] is True
    assert risk1["relevantText"] == "Client sha"

    # Legitimate evidence from clause must be verified and mapped to page 1 and clause 3
    risk2 = risks[1]
    assert risk2["title"] == "Invoice dispute window"
    assert risk2["evidence_unverified"] is False
    assert risk2["page"] == 1
    assert "3. Payment Obligations" in risk2["clause"]


@pytest.mark.anyio
async def test_genuinely_missing_payment_deadline_flagged():
    """Verify that a contract genuinely missing payment deadlines is correctly analyzed and supported."""
    missing_payment_doc = DocumentDetail(
        id="doc_missing_payment",
        filename="missing_payment_contract.pdf",
        uploadedAt="2026-10-18T00:00:00Z",
        status="ready",
        page_count=1,
        word_count=200,
        pages=[
            PageText(
                page_number=1,
                text=(
                    "1. Parties. Alpha and Beta enter this agreement.\n\n"
                    "2. Payment Obligations. Client shall pay fees for services rendered as mutually agreed.\n\n"
                    "3. Termination. Either party may terminate with 30 days notice.\n"
                )
            )
        ]
    )

    mock_model_response = {
        "overview": "Agreement without defined payment schedules.",
        "contract_type": "Services Agreement",
        "parties": ["Alpha", "Beta"],
        "effective_date": "Unspecified",
        "duration": "Unspecified",
        "key_obligations": ["Perform services"],
        "risks": [
            {
                "id": "risk-01",
                "severity": "high",
                "title": "Missing payment deadlines and billing schedule",
                "clause": "2. Payment Obligations",
                "explanation": "No payment due date, invoice period, or late fee interest rate is specified.",
                "relevantText": "Client shall pay fees for services rendered as mutually agreed.",
                "impact": "Uncertain cash flow and enforceability",
                "suggestion": "Specify due date such as 30 days after invoice",
            }
        ]
    }

    with patch("app.services.analysis_service.ollama_client.generate",
               new_callable=AsyncMock, return_value=json.dumps(mock_model_response)):
        res = await run_ai_document_analysis(missing_payment_doc)

    risks = res["risks"]
    assert len(risks) == 1
    assert risks[0]["severity"] == "high"
    assert risks[0]["title"] == "Missing payment deadlines and billing schedule"
    # Evidence is verbatim from the document, so it must be verified
    assert risks[0]["evidence_unverified"] is False
    assert risks[0]["page"] == 1
    assert "2. Payment Obligations" in risks[0]["clause"]


@pytest.mark.anyio
async def test_unsupported_or_hallucinated_evidence_marked_unverified():
    """Verify that fabricated or unrelated quotes are marked unverified."""
    doc = make_sample_contract_doc()

    mock_model_response = {
        "overview": "Overview",
        "contract_type": "Services Agreement",
        "parties": ["A", "B"],
        "effective_date": "Date",
        "duration": "Term",
        "key_obligations": ["Work"],
        "risks": [
            {
                "id": "risk-01",
                "severity": "medium",
                "title": "Hallucinated Penalty",
                "clause": "3. Payment Obligations",
                "explanation": "High late fee penalty",
                "relevantText": "Client shall forfeit fifty percent deposit upon cancellation of project",
                "impact": "Financial loss",
                "suggestion": "Remove forfeiture",
            }
        ]
    }

    with patch("app.services.analysis_service.ollama_client.generate",
               new_callable=AsyncMock, return_value=json.dumps(mock_model_response)):
        res = await run_ai_document_analysis(doc)

    risks = res["risks"]
    assert len(risks) == 1
    assert risks[0]["evidence_unverified"] is True


@pytest.mark.anyio
async def test_clause_7_full_text_retained_and_spans_pages():
    """Verify that Clause 7 (Limitation of Liability) includes both the liability cap and exclusion sentences."""
    doc = make_sample_contract_doc()
    clauses = chunk_document_into_candidate_clauses(doc)

    clause7 = next((c for c in clauses if "Limitation of Liability" in c["heading"]), None)
    assert clause7 is not None, "Clause 7 must be extracted"
    assert clause7["page"] == 1, "Clause 7 starts on page 1"

    text = clause7["text"]
    # Contains cap and exceptions
    assert "aggregate liability" in text
    assert "fees paid or payable" in text
    assert "payment obligations" in text
    assert "confidentiality" in text
    assert "indemnification" in text
    # Contains consequential damages exclusion across page 1 and 2
    assert "indirect" in text
    assert "consequential" in text


@pytest.mark.anyio
async def test_cross_page_evidence_verification_succeeds():
    """
    Verify that an excerpt spanning across page boundaries (such as the consequential damages sentence
    spanning from page 1 into page 2) is verified as valid evidence and correctly maps to the starting page and clause.
    """
    doc = make_sample_contract_doc()

    # The sentence from the screenshot that spans page 1 and page 2
    cross_page_quote = "Neither party shall be liable for indirect or consequential losses to the maximum extent permitted by applicable law."

    mock_model_response = {
        "overview": "Overview of sample contract",
        "contract_type": "Services Agreement",
        "parties": ["Example Client Ltd.", "Sample Solutions Pvt. Ltd."],
        "effective_date": "1 October 2026",
        "duration": "Unspecified",
        "key_obligations": ["Services"],
        "risks": [
            {
                "id": "risk-01",
                "severity": "medium",
                "title": "Review point: Scope of consequential damages exclusion",
                "clause": "7. Limitation of Liability",
                "explanation": "Review point: The limitation of liability clause excludes consequential losses to the maximum extent permitted by applicable law, subject to specified carve-outs.",
                "relevantText": cross_page_quote,
                "impact": "Excludes indirect damages recovery",
                "suggestion": "Verify that customary carve-outs align with commercial risk tolerance",
            }
        ]
    }

    with patch("app.services.analysis_service.ollama_client.generate",
               new_callable=AsyncMock, return_value=json.dumps(mock_model_response)):
        res = await run_ai_document_analysis(doc)

    risks = res["risks"]
    assert len(risks) == 1
    risk = risks[0]

    # Must NOT have Evidence Unverified badge
    assert risk["evidence_unverified"] is False, "Cross-page quotation must be verified"
    assert risk["page"] == 1, "Must attribute to the starting page (Page 1)"
    assert "7. Limitation of Liability" in risk["clause"]
    assert risk["relevantText"] == cross_page_quote


@pytest.mark.anyio
async def test_unsupported_cross_document_findings_remain_unverified():
    """
    Verify that findings attempting to assert cross-document or fabricated terms
    (e.g., 'unlimited liability for data breaches' or 'no defined support period'
    not present in lexiguard_sample_contract.pdf) have their evidence marked unverified
    and their priority penalized.
    """
    doc = make_sample_contract_doc()

    mock_model_response = {
        "overview": "Overview of sample contract",
        "contract_type": "Services Agreement",
        "parties": ["Example Client Ltd.", "Sample Solutions Pvt. Ltd."],
        "effective_date": "1 October 2026",
        "duration": "Unspecified",
        "key_obligations": ["Services"],
        "risks": [
            {
                "id": "risk-01",
                "severity": "high",
                "title": "Unlimited liability for data breaches",
                "clause": "7. Limitation of Liability",
                "explanation": "No cap on data breach damages in the agreement.",
                "relevantText": "Neither party liability shall be capped for security incidents or data breaches.",
                "impact": "Uncapped exposure",
                "suggestion": "Add data breach cap",
            },
            {
                "id": "risk-02",
                "severity": "medium",
                "title": "No defined support period for post-deployment issues",
                "clause": "1. Parties and Services",
                "explanation": "Post-deployment support period is undefined.",
                "relevantText": "Provider will provide technical support services for thirty days post-deployment.",
                "impact": "Uncertain support duration",
                "suggestion": "Clarify support duration",
            }
        ]
    }

    with patch("app.services.analysis_service.ollama_client.generate",
               new_callable=AsyncMock, return_value=json.dumps(mock_model_response)):
        res = await run_ai_document_analysis(doc)

    risks = res["risks"]
    assert len(risks) == 2

    # Both findings quote text that does NOT exist in lexiguard_sample_contract.pdf
    assert risks[0]["evidence_unverified"] is True
    assert risks[1]["evidence_unverified"] is True

    # High severity finding with unverified evidence should be penalized to Moderate tier (~35.0)
    assert risks[0]["priority_tier"] == "MODERATE"
    assert 30.0 <= risks[0]["priority_score"] <= 40.0
    assert risks[0]["priority_breakdown"]["factors"]["evidence_confidence"]["multiplier"] == 0.50


@pytest.mark.anyio
async def test_supported_termination_omission_finding_with_valid_clause_grounding():
    """
    Verify that an omission finding (e.g. lack of non-payment termination right)
    that quotes the actual source clause (Clause 5: material breach with 30-day cure)
    is verified and attributed to Page 1.
    """
    doc = make_sample_contract_doc()

    # The actual clause 5 termination text in the sample document
    clause_5_quote = "Either party may terminate this Agreement for a material breach if the breaching party fails to cure the breach within thirty days after receiving written notice."

    mock_model_response = {
        "overview": "Overview of sample contract",
        "contract_type": "Services Agreement",
        "parties": ["Example Client Ltd.", "Sample Solutions Pvt. Ltd."],
        "effective_date": "1 October 2026",
        "duration": "Unspecified",
        "key_obligations": ["Services"],
        "risks": [
            {
                "id": "risk-01",
                "severity": "medium",
                "title": "No explicit termination clause for non-payment",
                "clause": "5. Termination",
                "explanation": "Agreement requires a 30-day cure period for all material breaches, without an expedited termination remedy for payment defaults.",
                "relevantText": clause_5_quote,
                "impact": "Delayed remedy for non-payment",
                "suggestion": "Add immediate or 7-day termination upon non-payment",
            }
        ]
    }

    with patch("app.services.analysis_service.ollama_client.generate",
               new_callable=AsyncMock, return_value=json.dumps(mock_model_response)):
        res = await run_ai_document_analysis(doc)

    risks = res["risks"]
    assert len(risks) == 1
    risk = risks[0]

    # Quoting the actual clause 5 text must verify successfully
    assert risk["evidence_unverified"] is False
    assert risk["page"] == 1
    assert "5. Termination" in risk["clause"]
    assert risk["priority_breakdown"]["factors"]["evidence_confidence"]["multiplier"] == 1.0


@pytest.mark.anyio
async def test_classification_supported_contractual_omission_as_defect():
    """
    Regression Test 8.1:
    A clearly supported contractual omission (e.g. missing required non-payment termination remedy
    in a strictly bounded cure provision) is classified as `contractual_defect`.
    """
    doc = make_sample_contract_doc()
    clause_5_quote = "Either party may terminate this Agreement for a material breach if the breaching party fails to cure the breach within thirty days after receiving written notice."

    mock_model_response = {
        "overview": "Overview of sample contract",
        "contract_type": "Services Agreement",
        "parties": ["Example Client Ltd.", "Sample Solutions Pvt. Ltd."],
        "effective_date": "1 October 2026",
        "duration": "Unspecified",
        "key_obligations": ["Services"],
        "risks": [
            {
                "id": "risk-defect-1",
                "severity": "high",
                "finding_category": "contractual_defect",
                "title": "Omission of expedited payment default remedy",
                "clause": "5. Termination",
                "explanation": "Clause 5 subjects all material breaches to a thirty-day cure period without any expedited remedy or termination right for persistent payment defaults under Clause 3.",
                "relevantText": clause_5_quote,
                "impact": "Provider must wait 30 days after breach notice before terminating, even for total non-payment.",
                "suggestion": "Introduce a 7-day cure or immediate termination remedy for payment failures.",
            }
        ]
    }

    with patch("app.services.analysis_service.ollama_client.generate",
               new_callable=AsyncMock, return_value=json.dumps(mock_model_response)):
        res = await run_ai_document_analysis(doc)

    risks = res["risks"]
    assert len(risks) == 1
    defect = risks[0]
    assert defect["finding_category"] == "contractual_defect"
    assert defect["severity"] == "high"  # severity describes impact, distinct from category
    assert defect["evidence_unverified"] is False
    assert defect["page"] == 1
    assert "5. Termination" in defect["clause"]


@pytest.mark.anyio
async def test_classification_reasonable_negotiation_point_not_defective():
    """
    Regression Test 8.2:
    A reasonable negotiation point (e.g. standard 15-day invoice dispute window or mutual liability cap)
    must be classified as `negotiation_point` and NOT as a contractual defect.
    """
    doc = make_sample_contract_doc()
    dispute_quote = "Client may dispute an invoice in good faith by giving written notice within fifteen days."

    mock_model_response = {
        "overview": "Overview of sample contract",
        "contract_type": "Services Agreement",
        "parties": ["Example Client Ltd.", "Sample Solutions Pvt. Ltd."],
        "effective_date": "1 October 2026",
        "duration": "Unspecified",
        "key_obligations": ["Services"],
        "risks": [
            {
                "id": "risk-neg-1",
                "severity": "medium",
                "finding_category": "negotiation_point",
                "title": "Short invoice dispute notification window",
                "clause": "3. Payment Obligations",
                "explanation": "A fifteen-day invoice dispute period is common but moderately short for enterprise audit cycles. This is a commercial negotiation item rather than an inherent contract defect.",
                "relevantText": dispute_quote,
                "impact": "Operational risk of forfeiting invoice disputes if review takes longer than 15 days.",
                "suggestion": "Request extending the invoice dispute window to thirty days during contract negotiations.",
            }
        ]
    }

    with patch("app.services.analysis_service.ollama_client.generate",
               new_callable=AsyncMock, return_value=json.dumps(mock_model_response)):
        res = await run_ai_document_analysis(doc)

    risks = res["risks"]
    assert len(risks) == 1
    neg = risks[0]
    assert neg["finding_category"] == "negotiation_point"
    assert neg["finding_category"] != "contractual_defect"
    assert neg["severity"] == "medium"
    assert neg["evidence_unverified"] is False
    assert neg["page"] == 1


@pytest.mark.anyio
async def test_classification_insufficient_evidence_marked_unverified():
    """
    Regression Test 8.3:
    A finding with insufficient, hallucinated, or ungrounded evidence must have evidence_unverified = True,
    and fallback classification must preserve appropriate category and severity.
    """
    doc = make_sample_contract_doc()

    mock_model_response = {
        "overview": "Overview of sample contract",
        "contract_type": "Services Agreement",
        "parties": ["Example Client Ltd.", "Sample Solutions Pvt. Ltd."],
        "effective_date": "1 October 2026",
        "duration": "Unspecified",
        "key_obligations": ["Services"],
        "risks": [
            {
                "id": "risk-hallucinated-1",
                "severity": "high",
                "finding_category": "contractual_defect",
                "title": "Severe missing data breach indemnity",
                "clause": "4. Indemnification",
                "explanation": "The agreement completely omits data privacy indemnification.",
                "relevantText": "Provider shall indemnify Client for any unauthorized access to customer records occurred within 24 hours.",
                "impact": "Exposure to GDPR regulatory fines.",
                "suggestion": "Add GDPR data breach indemnification.",
            }
        ]
    }

    with patch("app.services.analysis_service.ollama_client.generate",
               new_callable=AsyncMock, return_value=json.dumps(mock_model_response)):
        res = await run_ai_document_analysis(doc)

    risks = res["risks"]
    assert len(risks) == 1
    finding = risks[0]
    # The quoted relevantText does not exist anywhere in the sample contract
    assert finding["evidence_unverified"] is True
    assert finding["finding_category"] == "contractual_defect"
    assert finding["severity"] == "high"
    # Priority tier must be penalized due to unverified evidence
    assert finding["priority_tier"] == "MODERATE"
    assert finding["priority_breakdown"]["factors"]["evidence_confidence"]["multiplier"] == 0.50


@pytest.mark.anyio
async def test_backward_compatibility_for_older_findings_without_category():
    """
    Regression Test 8.4:
    Verify that older finding structures without a `finding_category` field are safely normalized
    without crashes, default to appropriate category, and retain all existing fields.
    """
    doc = make_sample_contract_doc()

    # Legacy risk format: no 'finding_category' field
    legacy_model_response = {
        "overview": "Overview of sample contract",
        "contract_type": "Services Agreement",
        "parties": ["Example Client Ltd.", "Sample Solutions Pvt. Ltd."],
        "effective_date": "1 October 2026",
        "duration": "Unspecified",
        "key_obligations": ["Services"],
        "risks": [
            {
                "id": "legacy-risk-1",
                "severity": "critical",
                "title": "Omission of required IP ownership transfer",
                "clause": "1. Parties and Services",
                "explanation": "Agreement fails to transfer IP ownership to client upon payment.",
                "relevantText": "Provider will provide software implementation and technical support services described in mutually agreed written statements of work.",
                "impact": "Client might not own deliverables.",
                "suggestion": "Specify IP work made for hire transfer.",
            },
            {
                "id": "legacy-risk-2",
                "severity": "low",
                "title": "Notice method flexibility",
                "clause": "8. Notices and Amendments",
                "explanation": "Notices require tracked courier in addition to email, which is slightly rigid.",
                "relevantText": "Formal notices must be sent by email and by tracked courier to the contact details designated by each party in writing.",
                "impact": "Minor administrative overhead.",
                "suggestion": "Allow email notice alone.",
            }
        ]
    }

    with patch("app.services.analysis_service.ollama_client.generate",
               new_callable=AsyncMock, return_value=json.dumps(legacy_model_response)):
        res = await run_ai_document_analysis(doc)

    risks = res["risks"]
    assert len(risks) == 2

    # First legacy risk has "Omission", "fails to" and critical severity -> inferred contractual_defect
    assert risks[0]["finding_category"] == "contractual_defect"
    assert risks[0]["severity"] == "critical"
    assert risks[0]["evidence_unverified"] is False

    # Second legacy risk has low severity and flexible administrative note -> inferred negotiation_point or informational
    assert risks[1]["finding_category"] in ("negotiation_point", "informational")
    assert risks[1]["severity"] == "low"
    assert risks[1]["evidence_unverified"] is False


@pytest.mark.anyio
async def test_valid_source_references_and_page_spans_in_risks():
    """
    Regression Test 8.5:
    Verify that risks correctly capture valid source references and multi-page spans
    (e.g., Clause 7 spanning page 1 to 2 produces page_start=1, page_end=2, page_span='1-2').
    """
    doc = make_sample_contract_doc()
    # Clause 7 text starts on page 1 and ends on page 2:
    # "Except for payment obligations... Neither party shall be liable for indirect or consequential losses to the maximum extent permitted by applicable law."
    clause_7_quote = (
        "Except for payment obligations, confidentiality breaches, indemnification obligations, and liability that cannot legally be "
        "limited, neither party's aggregate liability arising from this Agreement shall exceed the fees paid or payable during the "
        "twelve months preceding the event giving rise to the claim."
    )

    mock_model_response = {
        "overview": "Overview of sample contract",
        "contract_type": "Services Agreement",
        "parties": ["Example Client Ltd.", "Sample Solutions Pvt. Ltd."],
        "effective_date": "1 October 2026",
        "duration": "Unspecified",
        "key_obligations": ["Services"],
        "risks": [
            {
                "id": "risk-span-1",
                "severity": "medium",
                "finding_category": "negotiation_point",
                "title": "12-month fees liability cap",
                "clause": "7. Limitation of Liability",
                "explanation": "The 12-month trailing fee cap is standard commercial practice, though Client may wish to negotiate a super-cap or higher multiple for data/confidentiality.",
                "relevantText": clause_7_quote,
                "impact": "Financial recovery limited to 12 months fees.",
                "suggestion": "Negotiate 2x multiplier or separate cap.",
            }
        ]
    }

    with patch("app.services.analysis_service.ollama_client.generate",
               new_callable=AsyncMock, return_value=json.dumps(mock_model_response)):
        res = await run_ai_document_analysis(doc)

    risks = res["risks"]
    assert len(risks) == 1
    risk = risks[0]

    assert risk["evidence_unverified"] is False
    assert "7. Limitation of Liability" in risk["clause"]
    # Clause 7 spans pages 1 and 2
    assert risk.get("page_start") == 1
    assert risk.get("page_end") == 2
    assert risk.get("page_span") == "1-2"
    assert risk["page"] == 1  # backwards compatibility

