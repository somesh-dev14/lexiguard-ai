from app.schemas.document import DocumentDetail, PageText
from app.services.analysis_service import _source_summary, _is_placeholder


def make_doc(text: str) -> DocumentDetail:
    return DocumentDetail(
        id="doc-test",
        filename="sample.pdf",
        page_count=1,
        word_count=len(text.split()),
        uploadedAt="2026-10-18T00:00:00Z",
        status="ready",
        demo_mode=False,
        pages=[PageText(page_number=1, text=text)],
    )


def test_placeholder_detection_handles_schema_examples():
    assert _is_placeholder("Identified Parties")
    assert _is_placeholder("Effective date or 'Not explicitly specified'")
    assert _is_placeholder("Obligation 1")
    assert not _is_placeholder("Example Client Pvt. Ltd.")


def test_summary_fields_are_repaired_from_source_text():
    text = (
        "SAMPLE SERVICES AGREEMENT\n"
        "Example Client Pvt. Ltd. (Client) and Sample Technology Services Pvt. Ltd. (Provider).\n"
        "1. Services and Term\n"
        "Provider will deliver website maintenance and technical support. "
        "This agreement begins on 1 November 2026 and continues for twelve months unless terminated earlier."
    )
    current = {
        "overview": "Legal contract processed with DeBERTa clause classifier and Ollama intelligence.",
        "contract_type": "Commercial Agreement",
        "parties": ["Identified Parties"],
        "effective_date": "Effective date or 'Not explicitly specified'",
        "duration": "Unspecified",
        "key_obligations": ["Obligation 1", "Obligation 2", "Obligation 3"],
    }
    result = _source_summary(
        make_doc(text),
        current,
        [{"heading": "1. Services and Term", "text": "Provider will deliver website maintenance and technical support.", "page": 1}],
    )
    assert result["parties"] == ["Example Client Pvt. Ltd.", "Sample Technology Services Pvt. Ltd."]
    assert result["effective_date"] == "1 November 2026"
    assert result["duration"] == "twelve months"
    assert result["key_obligations"] == ["Provider will deliver website maintenance and technical support."]
    assert "processed with DeBERTa" not in result["overview"]
    assert "Identified Parties" not in str(result)



def test_unverified_model_party_is_replaced_from_source():
    text = (
        "SAMPLE SERVICES AGREEMENT\n"
        "Example Client Pvt. Ltd. (Client) and Sample Technology Services Pvt. Ltd. (Provider).\n"
        "1. Services\n"
        "Provider will deliver website maintenance and technical support."
    )
    current = {
        "overview": "No reliable overview could be extracted from the document text.",
        "contract_type": "Services Agreement",
        "parties": ["You1"],
        "effective_date": "Not explicitly specified",
        "duration": "Not explicitly specified",
        "key_obligations": ["Obligation 1", "Obligation 2"],
    }
    result = _source_summary(
        make_doc(text),
        current,
        [{"heading": "1. Services", "text": "1. Services Provider will deliver website maintenance and technical support.", "page": 1}],
    )
    assert result["parties"] == ["Example Client Pvt. Ltd.", "Sample Technology Services Pvt. Ltd."]
    assert result["overview"] != "No reliable overview could be extracted from the document text."


def test_generic_obligations_are_rebuilt_from_clause_text():
    text = (
        "SAMPLE SERVICES AGREEMENT\n"
        "Example Client Pvt. Ltd. (Client) and Sample Technology Services Pvt. Ltd. (Provider).\n"
        "1. Services\n"
        "Provider will deliver website maintenance and technical support."
    )
    current = {
        "overview": "A services agreement.",
        "contract_type": "Services Agreement",
        "parties": ["Example Client Pvt. Ltd.", "Sample Technology Services Pvt. Ltd."],
        "effective_date": "Not explicitly specified",
        "duration": "Not explicitly specified",
        "key_obligations": [
            "Maintain confidentiality of proprietary information",
            "Comply with applicable governing laws and dispute resolution terms",
        ],
    }
    result = _source_summary(
        make_doc(text),
        current,
        [{"heading": "1. Services", "text": "Provider will deliver website maintenance and technical support.", "page": 1}],
    )
    assert result["key_obligations"] == ["Provider will deliver website maintenance and technical support."]


def test_key_obligations_prioritizes_numerical_deadlines_and_financial_terms():
    """Verifies that material financial and procedural deadlines outrank generic statements."""
    text = (
        "1. Services. Provider will provide software implementation and consulting services.\n"
        "2. Confidentiality. Each party shall hold proprietary information in confidence.\n"
        "3. Payment. Client shall pay Provider a fee of INR 120,000 within thirty (30) days of invoice. "
        "Overdue undisputed amounts shall accrue interest at the rate of 1.5% per month. "
        "Client may dispute an invoice within fifteen (15) days of receipt.\n"
        "4. Security. Provider shall notify Client of any confirmed security incident within twenty-four (24) hours.\n"
        "5. Termination. Either party may terminate for material breach if not cured within thirty (30) days."
    )
    clauses = [
        {"heading": "1. Services", "text": "Provider will provide software implementation and consulting services.", "page": 1},
        {"heading": "2. Confidentiality", "text": "Each party shall hold proprietary information in confidence.", "page": 1},
        {"heading": "3. Payment", "text": "Client shall pay Provider a fee of INR 120,000 within thirty (30) days of invoice. Overdue undisputed amounts shall accrue interest at the rate of 1.5% per month. Client may dispute an invoice within fifteen (15) days of receipt.", "page": 1},
        {"heading": "4. Security", "text": "Provider shall notify Client of any confirmed security incident within twenty-four (24) hours.", "page": 2},
        {"heading": "5. Termination", "text": "Either party may terminate for material breach if not cured within thirty (30) days.", "page": 2},
    ]
    raw_summary = {
        "overview": "Service contract",
        "contract_type": "Services Agreement",
        "parties": ["Client", "Provider"],
        "effective_date": "Not explicitly specified",
        "duration": "Not explicitly specified",
        "key_obligations": ["Obligation 1", "Obligation 2"],  # invalid/placeholder
    }
    repaired = _source_summary(make_doc(text), raw_summary, clauses)
    obligations = repaired["key_obligations"]

    assert len(obligations) <= 5
    # Material financial/deadline obligations must be present
    assert any("INR 120,000" in o and "thirty (30) days" in o for o in obligations)
    assert any("1.5% per month" in o for o in obligations)
    assert any("fifteen (15) days" in o for o in obligations)
    assert any("twenty-four (24) hours" in o for o in obligations)
    assert any("cured within thirty (30) days" in o for o in obligations)


def test_key_obligations_deduplicates_overlapping_statements():
    """Verifies near-identical obligation statements across clauses are deduplicated."""
    text = (
        "1. Payment. Client shall pay the service fee of $50,000 within thirty days.\n"
        "2. Billing Terms. Client shall pay the service fee of $50,000 within thirty days.\n"
        "3. Support. Provider will provide technical support responses within 4 hours."
    )
    clauses = [
        {"heading": "1. Payment", "text": "Client shall pay the service fee of $50,000 within thirty days.", "page": 1},
        {"heading": "2. Billing", "text": "Client shall pay the service fee of $50,000 within thirty days.", "page": 1},
        {"heading": "3. Support", "text": "Provider will provide technical support responses within 4 hours.", "page": 2},
    ]
    raw_summary = {
        "overview": "Overview",
        "contract_type": "Commercial Agreement",
        "parties": ["Party A", "Party B"],
        "effective_date": "Unspecified",
        "duration": "Unspecified",
        "key_obligations": [],
    }
    repaired = _source_summary(make_doc(text), raw_summary, clauses)
    obligations = repaired["key_obligations"]

    assert len(obligations) == 2
    # Only 1 payment obligation must be retained, not 2 identical ones
    assert sum(1 for o in obligations if "$50,000" in o) == 1
    assert any("within 4 hours" in o for o in obligations)


def test_key_obligations_gracefully_handles_absent_obligations():
    """Verifies that contracts with no binding modal commitments yield a clean fallback."""
    text = "SCHEDULE A\nTable of item codes: 101, 102, 103.\nNo commitments specified."
    clauses = [
        {"heading": "Schedule A", "text": "Table of item codes: 101, 102, 103. No commitments specified.", "page": 1}
    ]
    raw_summary = {
        "overview": "Exhibit",
        "contract_type": "Exhibit",
        "parties": ["Not specified"],
        "effective_date": "Not specified",
        "duration": "Not specified",
        "key_obligations": [],
    }
    repaired = _source_summary(make_doc(text), raw_summary, clauses)
    assert repaired["key_obligations"] == ["No clear operative obligations could be reliably extracted."]
