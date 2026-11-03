"""
Comprehensive regression tests for executive summary repair, party extraction,
clause heading preservation, risk grounding, and report integrity.
"""

import json
import pytest
from unittest.mock import patch, AsyncMock

from app.services.analysis_service import (
    _source_summary,
    _is_placeholder,
    _extract_grounded_parties,
    chunk_document_into_candidate_clauses,
    run_ai_document_analysis,
)
from app.schemas.document import DocumentDetail, PageText
from tests.test_risk_analysis_regression import make_sample_contract_doc, SAMPLE_CONTRACT_PAGE_1, SAMPLE_CONTRACT_PAGE_2


def test_is_placeholder_rejects_you1_and_schema_artifacts():
    assert _is_placeholder("You1") is True
    assert _is_placeholder("you2") is True
    assert _is_placeholder("Party A") is True
    assert _is_placeholder("Party 1") is True
    assert _is_placeholder("Identified Parties") is True
    assert _is_placeholder("No readable text was extracted from this PDF.") is True
    assert _is_placeholder("Example Client Ltd.") is False
    assert _is_placeholder("Sample Solutions Pvt. Ltd.") is False


def test_extract_grounded_parties_from_contract_text():
    parties = _extract_grounded_parties(SAMPLE_CONTRACT_PAGE_1)
    assert len(parties) >= 2
    assert any("Example Client" in p for p in parties)
    assert any("Sample Solutions" in p for p in parties)
    # Ensure 'You1' or title artifacts are never extracted
    assert not any("You1" in p for p in parties)
    assert not any("SAMPLE SERVICES AGREEMENT" in p for p in parties)


def test_source_summary_repairs_you1_and_broken_overview():
    doc = make_sample_contract_doc()
    clauses = chunk_document_into_candidate_clauses(doc)

    raw_summary = {
        "overview": "No reliable overview could be extracted from the document text.",
        "contract_type": "The formal contract category",
        "parties": ["You1"],
        "effective_date": "Effective date or not explicitly specified",
        "duration": "Term duration or unspecified",
        "key_obligations": ["obligation 1", "obligation 2"],
    }

    repaired = _source_summary(doc, raw_summary, clauses)

    # 1. Parties repaired from source text
    assert len(repaired["parties"]) >= 2
    assert "You1" not in repaired["parties"]
    assert any("Example Client" in p for p in repaired["parties"])
    assert any("Sample Solutions" in p for p in repaired["parties"])

    # 2. Overview repaired with source-grounded text, not error string
    assert "No reliable overview could be extracted" not in repaired["overview"]
    assert "Services Agreement" in repaired["overview"] or "Example Client" in repaired["overview"]

    # 3. Contract type repaired
    assert repaired["contract_type"] != "The formal contract category"
    assert "Services Agreement" in repaired["contract_type"]

    # 4. Effective date extracted
    assert "1 October 2026" in repaired["effective_date"]

    # 5. Key obligations extracted from real clauses, not placeholders
    assert len(repaired["key_obligations"]) >= 1
    assert not any("obligation 1" in o.lower() for o in repaired["key_obligations"])


@pytest.mark.anyio
async def test_classified_clauses_preserve_original_heading_and_predicted_category():
    doc = make_sample_contract_doc()

    mock_model_response = {
        "overview": "Overview of sample contract",
        "contract_type": "Services Agreement",
        "parties": ["Example Client Ltd.", "Sample Solutions Pvt. Ltd."],
        "effective_date": "1 October 2026",
        "duration": "Unspecified",
        "key_obligations": ["Provide services"],
        "risks": []
    }

    with patch("app.services.analysis_service.ollama_client.generate",
               new_callable=AsyncMock, return_value=json.dumps(mock_model_response)):
        res = await run_ai_document_analysis(doc)

    clauses = res["clauses"]
    assert len(clauses) >= 7

    # Find Payment Obligations clause
    payment_clause = next((c for c in clauses if "Payment Obligations" in c.get("original_heading", "")), None)
    assert payment_clause is not None
    assert payment_clause["original_heading"] == "3. Payment Obligations"
    assert "predicted_category" in payment_clause
    assert payment_clause["page"] == 1
