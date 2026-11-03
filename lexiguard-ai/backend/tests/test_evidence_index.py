"""
Tests for the experimental evidence index and the B1 retrieval QA mode.

Dense embeddings and the cross-encoder are switched off here so the tests
stay fast and do not need torch; the retrieval path is exercised with BM25.
"""

import fitz
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.core.config import settings
from app.main import app
from app.schemas.document import DocumentDetail, PageText
from app.services.chat_service import answer_document_question
from app.services.evidence import enrich, store as evidence_store
from app.services.evidence.index import build_evidence_index
from app.services.evidence.retriever import retrieve, format_context
from tests.test_chat_regression import make_sample_doc


CONTRACT_P1 = (
    "MASTER SERVICES AGREEMENT\n\n"
    'This Agreement (the "Agreement") is made between Northwind Ltd (the "Supplier") '
    'and Contoso Ltd (the "Customer").\n\n'
    "1. Definitions\n"
    '1.1 "Early Termination Fee" means the Charges for the three (3) months before termination.\n'
    '"Service Levels" means the standards set out in Schedule 2.\n\n'
    "12. Limitation of Liability\n"
    "12.2 Subject to Section 12.3, total liability shall not exceed the Charges paid in twelve months.\n"
    "12.3 Notwithstanding Section 12.2, the cap shall not apply to breach of Sections 8 and 11.1.\n\n"
    "14. Termination\n"
    "14.1 Termination for convenience. The Customer may terminate on sixty (60) days' notice, "
    "subject to payment of the Early Termination Fee.\n"
    "14.2 Termination for cause. The Customer may terminate under this Section 14.2 for material breach.\n"
)
CONTRACT_P2 = (
    "SCHEDULE 2 - SERVICE LEVELS\n"
    "1.1 Availability shall be 99.5% in each calendar month.\n"
)


def make_contract():
    return DocumentDetail(
        id="doc_evidence_test", filename="msa.pdf", page_count=2, word_count=200,
        uploadedAt="2026-01-01T00:00:00Z", status="ready", demo_mode=False,
        pages=[PageText(page_number=1, text=CONTRACT_P1), PageText(page_number=2, text=CONTRACT_P2)],
    )


@pytest.fixture
def lexical_only(monkeypatch):
    monkeypatch.setattr(settings, "EVIDENCE_DENSE_ENABLED", False)
    monkeypatch.setattr(settings, "EVIDENCE_RERANK_ENABLED", False)
    evidence_store.clear()
    yield
    evidence_store.clear()


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------

def test_parse_section_number():
    assert enrich.parse_section_number("14.2 Termination for cause") == "14.2"
    assert enrich.parse_section_number("3. Payment Obligations") == "3"
    assert enrich.parse_section_number("Section 7.1: Fees") == "7.1"
    assert enrich.parse_section_number("Preamble") is None


def test_declared_terms_quoted_only():
    text = '"Early Termination Fee" means X. This Agreement (the "Agreement") between A (Provider).'
    assert enrich.extract_declared_terms(text) == ["Early Termination Fee", "Agreement"]


def test_cross_references_include_lists():
    text = "Notwithstanding Section 12.2, the cap shall not apply to Sections 8 and 11.1(a)."
    assert enrich.extract_cross_references(text) == ["12.2", "8", "11.1"]


def test_attachment_references():
    assert enrich.extract_attachment_references("as set out in Schedule 2 and Exhibit A") == ["Schedule 2", "Exhibit A"]


def test_modifiers():
    mods = enrich.extract_modifiers("Notwithstanding Section 14.1, subject to Section 9, this shall not apply.")
    assert {"notwithstanding", "subject_to", "shall_not_apply"} <= set(mods)


def test_resolve_section_prefix_fallback():
    section_map = {"4": "a", "4.2": "b"}
    assert enrich.resolve_section("4.2", section_map) == "b"
    assert enrich.resolve_section("4.2.1", section_map) == "b"
    assert enrich.resolve_section("4.7", section_map) == "a"
    assert enrich.resolve_section("9", section_map) is None


# ---------------------------------------------------------------------------
# Segmentation and index structure
# ---------------------------------------------------------------------------

def test_index_structure():
    ix = build_evidence_index(make_contract())
    by_section = {c.section: c for c in ix.clauses if c.attachment is None and c.section}

    # Preamble kept even though the analysis chunker drops it
    assert ix.clauses[0].heading == "Preamble"
    assert "Supplier" in ix.clauses[0].declares_terms

    # Subsections without a trailing dot ("14.2 Termination") are split out
    assert {"1.1", "12.2", "12.3", "14.1", "14.2"} <= set(by_section)
    assert by_section["14.2"].page_span == "1"

    # Definitions map to their clause; uses are recorded
    assert ix.definitions["Early Termination Fee"] == by_section["1.1"].id
    assert "Early Termination Fee" in by_section["14.1"].uses_terms

    # Cross-references resolve; self-references are dropped
    assert by_section["12.3"].xref_targets["12.2"] == by_section["12.2"].id
    assert by_section["12.3"].xref_targets["8"] is None          # Section 8 not in this document
    assert "14.2" not in by_section["14.2"].xrefs
    assert "notwithstanding" in by_section["12.3"].modifiers

    # Attachments are split, and their internal "1.1" does not shadow main-body 1.1
    assert "Schedule 2" in ix.attachment_map
    sched = ix.clause(ix.attachment_map["Schedule 2"])
    assert sched.page_start == 2
    assert ix.section_map["1.1"] == by_section["1.1"].id
    assert by_section["1.1"].attachment_targets["Schedule 2"] == sched.id


def test_index_on_sample_contract_has_all_clauses():
    ix = build_evidence_index(make_sample_doc())
    headings = [c.heading for c in ix.clauses]
    assert headings[0] == "Preamble"
    assert any(h.startswith("3. Payment Obligations") for h in headings)
    assert any(h.startswith("8. Notices") for h in headings)
    assert ix.dense is None  # dense is opt-in


# ---------------------------------------------------------------------------
# Oversized clause splitting
# ---------------------------------------------------------------------------

from app.services.evidence.index import split_oversized, document_text


def _long_text():
    paras = []
    for i in range(12):
        sentences = " ".join(f"Sentence {i}.{j} sets out an obligation of the Parties under this Agreement." for j in range(6))
        paras.append(f"({i}) {sentences}")
    return "\n\n".join(paras)


def test_split_oversized_windows_are_ordered_substrings():
    text = _long_text()
    parts = split_oversized(text, 1000)
    assert len(parts) > 1
    assert all(len(p) <= 1000 * 1.2 for p in parts)
    pos = 0
    for p in parts:
        idx = text.find(p, pos)
        assert idx >= pos            # exact substring, in order
        pos = idx + len(p)
    # nothing but whitespace is lost
    assert "".join(parts).replace(" ", "").replace("\n", "") == text.replace(" ", "").replace("\n", "")


def test_split_oversized_prefers_paragraph_boundaries():
    text = _long_text()
    parts = split_oversized(text, 1000)
    assert all(p.startswith("(") for p in parts)   # every window starts at a paragraph


def test_split_oversized_handles_text_without_boundaries():
    text = "word " * 1000
    parts = split_oversized(text, 700)
    assert all(len(p) <= 700 * 1.2 for p in parts) and len(parts) >= 7


def test_split_oversized_disabled_or_short():
    assert split_oversized("short clause", 1000) == ["short clause"]
    assert split_oversized(_long_text(), 0) == [_long_text().strip()]


def test_index_splits_long_clause_into_located_parts(monkeypatch):
    monkeypatch.setattr(settings, "EVIDENCE_MAX_CLAUSE_CHARS", 1000)
    body = "5. Obligations\n" + _long_text()
    doc = DocumentDetail(id="d", filename="d", page_count=1, word_count=1, uploadedAt="", status="ready",
                         pages=[PageText(page_number=1, text=body)])
    ix = build_evidence_index(doc)
    parts = [c for c in ix.clauses if c.section == "5"]
    assert len(parts) > 1
    assert parts[1].heading == "5. Obligations (part 2)" and parts[1].parent_id == parts[0].id
    assert ix.section_map["5"] == parts[0].id
    full = document_text(doc)
    for c in ix.clauses:
        assert c.char_start is not None
        assert " ".join(full[c.char_start:c.char_end].split()) == " ".join(c.text.split())
    assert ix.build_info["longest_clause_chars"] <= 1200
    # continuation parts are searched with their heading for context
    assert parts[1].search_text.startswith("5. Obligations (part 2)")


# ---------------------------------------------------------------------------
# Retrieval (BM25 only)
# ---------------------------------------------------------------------------

def test_bm25_ranks_payment_clause_first(lexical_only):
    ix = build_evidence_index(make_sample_doc())
    res = retrieve(ix, "What are the payment terms and penalties for late payment?")
    assert res["components"] == {"bm25": True, "dense": False, "rerank": False}
    assert ix.clause(res["hits"][0].clause_id).heading.startswith("3. Payment")


def test_format_context_skips_whole_clauses_over_budget(lexical_only):
    ix = build_evidence_index(make_sample_doc())
    hits = retrieve(ix, "party agreement notice terminate liability", top_k=8)["hits"]
    assert len(hits) >= 2
    out = format_context(ix, hits, max_chars=len(ix.clause(hits[0].clause_id).text) + 60)
    assert out["used"] == [hits[0].clause_id]
    assert out["dropped"]
    assert ix.clause(hits[0].clause_id).text.strip() in out["context"]


# ---------------------------------------------------------------------------
# Chat QA modes
# ---------------------------------------------------------------------------

def _mock_response():
    return '{"answer": "Payment is due within thirty (30) days.", "sources": [{"page": 1, "excerpt": "within thirty (30) days of receipt"}]}'


@pytest.mark.anyio
async def test_baseline_mode_is_default_and_unchanged(lexical_only):
    assert settings.QA_MODE == "baseline"
    captured = {}

    async def capture(prompt, system_prompt=None, **kwargs):
        captured["prompt"], captured["system"] = prompt, system_prompt
        return _mock_response()

    with patch("app.services.chat_service.ollama_client.generate", side_effect=capture):
        result = await answer_document_question(make_sample_doc(), "What are the payment terms?")

    assert "--- Page 1 ---" in captured["prompt"] and "--- Page 2 ---" in captured["prompt"]
    assert "Governing Law" in captured["prompt"]
    assert "retrieved" not in captured["system"]
    assert "retrieval" not in result and "qa_mode" not in result


@pytest.mark.anyio
async def test_retrieval_mode_uses_only_retrieved_clauses(lexical_only, monkeypatch):
    monkeypatch.setattr(settings, "QA_MODE", "retrieval")
    captured = {}

    async def capture(prompt, system_prompt=None, **kwargs):
        captured["prompt"], captured["system"] = prompt, system_prompt
        return _mock_response()

    with patch("app.services.chat_service.ollama_client.generate", side_effect=capture):
        result = await answer_document_question(make_sample_doc(), "What are the payment terms and penalties for late payment?")

    assert "3. Payment Obligations" in captured["prompt"]
    assert "Governing Law" not in captured["prompt"]
    assert "retrieved" in captured["system"]
    assert result["qa_mode"] == "retrieval"
    assert result["retrieval"]["clauses"][0]["heading"].startswith("3. Payment")
    assert result["sources"][0]["excerpt_verified"] is True


@pytest.mark.anyio
async def test_retrieval_mode_falls_back_when_nothing_matches(lexical_only, monkeypatch):
    monkeypatch.setattr(settings, "QA_MODE", "retrieval")
    captured = {}

    async def capture(prompt, system_prompt=None, **kwargs):
        captured["prompt"] = prompt
        return _mock_response()

    with patch("app.services.chat_service.ollama_client.generate", side_effect=capture):
        result = await answer_document_question(make_sample_doc(), "xylophone zebra quasar?")

    assert result["retrieval"]["fallback"] == "full_document"
    assert "--- Page 2 ---" in captured["prompt"]


# ---------------------------------------------------------------------------
# Upload / delete wiring
# ---------------------------------------------------------------------------

def test_upload_builds_index_and_delete_removes_it(lexical_only):
    client = TestClient(app)
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((50, 72), "1. Payment Terms. Client shall pay within 30 days.\n2. Governing Law. Laws of India.")
    data = pdf.tobytes()
    pdf.close()

    res = client.post("/api/documents/upload", files={"file": ("t.pdf", data, "application/pdf")})
    assert res.status_code == 200
    doc_id = res.json()["id"]
    assert "evidence" not in res.json()  # response schema unchanged

    ix = evidence_store.get(doc_id)
    assert ix is not None and ix.dense is None  # baseline mode: no dense at upload
    assert len(ix.clauses) >= 2

    client.delete(f"/api/documents/{doc_id}")
    assert evidence_store.get(doc_id) is None
