from fastapi.testclient import TestClient
from app.main import app
import fitz

client = TestClient(app)

def test_pdf_upload():
    # Generate in-memory PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "CONFIDENTIALITY AGREEMENT\nThis Agreement is entered into by Party A and Party B.")
    pdf_bytes = doc.write()
    doc.close()

    # Upload
    files = {"file": ("test_agreement.pdf", pdf_bytes, "application/pdf")}
    res = client.post("/api/documents/upload", files=files)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["filename"] == "test_agreement.pdf"
    assert data["page_count"] == 1
    assert data["word_count"] > 0
    assert len(data["pages"]) == 1
    assert "CONFIDENTIALITY" in data["pages"][0]["text"]

    doc_id = data["id"]

    # Verify retrieval
    res_get = client.get(f"/api/documents/{doc_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == doc_id

    # Verify analysis (mock Ollama to ensure deterministic test execution across environments)
    from unittest.mock import patch, AsyncMock
    mock_ollama_json = (
        '{"overview": "Confidentiality Agreement between Party A and Party B.", '
        '"contract_type": "Confidentiality Agreement", '
        '"parties": ["Party A", "Party B"], '
        '"effective_date": "Upon Execution", '
        '"duration": "12 months", '
        '"key_obligations": ["Hold confidential info in strict confidence"], '
        '"risks": []}'
    )
    with patch("app.services.analysis_service.ollama_client.generate", new_callable=AsyncMock, return_value=mock_ollama_json):
        res_an = client.get(f"/api/documents/{doc_id}/analysis")
        assert res_an.status_code == 200
        assert res_an.json()["document_id"] == doc_id

    # Verify delete
    res_del = client.delete(f"/api/documents/{doc_id}")
    assert res_del.status_code == 200
    assert res_del.json()["success"] is True

    print("ALL BACKEND PDF INTEGRATION TESTS PASSED!")

def test_fresh_upload_navigates_to_valid_analysis_route():
    """
    Regression test:
    Confirms upload returns exact document_id, which can be looked up directly
    via GET /api/documents/{id} and GET /api/documents/{id}/analysis without
    stale browser storage or hardcoded IDs.
    """
    import fitz
    from unittest.mock import patch, AsyncMock

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "1. Termination Clause. Either party may terminate with 30 days notice.")
    pdf_bytes = doc.write()
    doc.close()

    # 1. Fresh upload
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("vendor_agreement.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    upload_doc_id = upload_data["id"]
    assert upload_doc_id.startswith("doc_")

    # 2. Direct document fetch (matches frontend fetchDocumentById)
    doc_res = client.get(f"/api/documents/{upload_doc_id}")
    assert doc_res.status_code == 200
    assert doc_res.json()["id"] == upload_doc_id
    assert doc_res.json()["filename"] == "vendor_agreement.pdf"

    # 3. Direct analysis fetch (matches AnalysisPage route load)
    mock_summary_json = (
        '{"overview": "Vendor contract with termination rights.", '
        '"contract_type": "Vendor Agreement", '
        '"parties": ["Vendor", "Client"], '
        '"effective_date": "2026-01-01", '
        '"duration": "1 year", '
        '"key_obligations": ["Provide services"], '
        '"risks": []}'
    )
    with patch("app.services.analysis_service.ollama_client.generate", new_callable=AsyncMock, return_value=mock_summary_json):
        analysis_res = client.get(f"/api/documents/{upload_doc_id}/analysis")
        assert analysis_res.status_code == 200
        analysis_data = analysis_res.json()
        assert analysis_data["document_id"] == upload_doc_id

    # 4. Clean up
    client.delete(f"/api/documents/{upload_doc_id}")

if __name__ == "__main__":
    test_pdf_upload()
    test_fresh_upload_navigates_to_valid_analysis_route()