"""
Chat Service for LexiGuard AI
Provides document-grounded Q&A using Ollama (RAG-style retrieval over extracted pages).
Each query is answered using ONLY the text from the specified document's pages.
Citations are validated against the document's actual page count.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional

import anyio

from app.core.config import settings
from app.schemas.document import DocumentDetail
from app.services.ollama_client import ollama_client

logger = logging.getLogger("lexiguard.chat")


def _build_page_context(doc: DocumentDetail, max_chars_per_page: int = 3000) -> str:
    """
    Builds a structured context string from the document's extracted pages.
    Each page is clearly delineated with its page number for citation grounding.
    """
    if not doc.pages:
        return ""

    parts: List[str] = []
    for page in doc.pages:
        text = (page.text or "").strip()
        if not text:
            continue
        # Truncate very long pages to stay within prompt limits
        if len(text) > max_chars_per_page:
            text = text[:max_chars_per_page] + "..."
        parts.append(f"--- Page {page.page_number} ---\n{text}")

    return "\n\n".join(parts)


def _find_relevant_pages(doc: DocumentDetail, question: str) -> List[Dict[str, Any]]:
    """
    Simple keyword-based relevance scoring to identify which pages are most
    relevant to the question. Returns all pages with their text, sorted by
    relevance score (descending).
    """
    if not doc.pages:
        return []

    # Extract meaningful keywords from the question (>= 3 chars, not stopwords)
    stopwords = {
        "the", "and", "for", "are", "what", "how", "who", "when", "where",
        "which", "this", "that", "with", "from", "have", "has", "does", "can",
        "will", "shall", "any", "all", "not", "but", "about", "under",
    }
    words = re.findall(r"[a-zA-Z]+", question.lower())
    keywords = [w for w in words if len(w) >= 3 and w not in stopwords]

    scored_pages = []
    for page in doc.pages:
        text_lower = (page.text or "").lower()
        if not text_lower.strip():
            continue
        score = sum(1 for kw in keywords if kw in text_lower)
        scored_pages.append({
            "page_number": page.page_number,
            "text": page.text,
            "relevance_score": score,
        })

    # Sort by relevance, highest first
    scored_pages.sort(key=lambda p: p["relevance_score"], reverse=True)
    return scored_pages


def _validate_page_citations(
    sources: List[Dict[str, Any]],
    doc: DocumentDetail,
) -> List[Dict[str, Any]]:
    """
    Validates that cited page numbers actually exist in the document.
    Removes citations with nonexistent pages. Verifies that excerpts
    appear in the cited page's text.
    """
    valid_pages = {p.page_number: p.text for p in doc.pages}
    validated: List[Dict[str, Any]] = []

    for src in sources:
        page_num = src.get("page")
        if page_num is None or page_num not in valid_pages:
            logger.warning(
                "Chat citation references nonexistent page %s (doc has %d pages), dropping",
                page_num,
                len(valid_pages),
            )
            continue

        # Verify excerpt exists in the cited page
        excerpt = (src.get("excerpt") or "").strip()
        page_text = valid_pages[page_num]
        excerpt_verified = False

        def _norm_tokens(s: str) -> str:
            return " ".join(re.findall(r"[a-zA-Z0-9]+", s.lower()))

        if excerpt and len(excerpt) >= 6:
            norm_excerpt = _norm_tokens(excerpt)
            norm_page = _norm_tokens(page_text)
            excerpt_verified = (excerpt.lower() in page_text.lower()) or (norm_excerpt and norm_excerpt in norm_page)
            if not excerpt_verified:
                # Check if the excerpt appears on any page (model may have cited wrong page)
                for pn, pt in valid_pages.items():
                    norm_pt = _norm_tokens(pt)
                    if (excerpt.lower() in pt.lower()) or (norm_excerpt and norm_excerpt in norm_pt):
                        src["page"] = pn
                        excerpt_verified = True
                        logger.info(
                            "Chat citation excerpt found on page %d instead of cited page %d, correcting",
                            pn, page_num,
                        )
                        break

        src["excerpt_verified"] = excerpt_verified
        validated.append(src)

    return validated


def _sanitize_chat_answer(answer: str) -> str:
    """
    Strips internal monologue, meta-narration, prompt echoes, and thinking patterns
    from chat answers to ensure only concise, professional legal answers reach users.
    """
    if not answer:
        return ""

    # 1. Strip chain-of-thought tags if present
    cleaned = re.sub(r"(?i)<think>[\s\S]*?</think>", "", answer)
    cleaned = re.sub(r"(?i)</?think>", "", cleaned)

    # 2. Strip meta-narration phrases where the model narrates its own prompt instructions or steps
    meta_phrases = [
        r"(?i)(?:now\s+)?we\s+need\s+to\s+(?:extract|find|quote|identify|check)[\s\S]*?(?:[\.\:\n]|$)",
        r"(?i)let(?:'s|s)\s+(?:check|see|look|find|extract|analyze)[\s\S]*?(?:[\.\:\n]|$)",
        r"(?i)based\s+on\s+the\s+instructions[\s\S]*?(?:[\.\:\n]|$)",
        r"(?i)here\s+is\s+the\s+(?:direct\s+)?answer[\s\S]*?[\:\n]",
        r"(?i)according\s+to\s+the\s+prompt[\s\S]*?(?:[\.\:\n]|$)",
        r"(?i)i\s+will\s+(?:now\s+)?answer[\s\S]*?(?:[\.\:\n]|$)",
    ]
    for pat in meta_phrases:
        cleaned = re.sub(pat, "", cleaned)

    # 3. Clean incomplete trailing sentences if response was truncated mid-sentence
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if lines:
        last_line = lines[-1]
        # If the last line is a dangling clause ending without punctuation (and not a bullet)
        if len(last_line) > 10 and not last_line.endswith(('.', ':', '!', '?', '"', "'", ')', '`')):
            # If there are preceding complete sentences/bullets, drop the dangling fragment
            if len(lines) > 1:
                lines = lines[:-1]
            else:
                lines[-1] = last_line + "..."
    cleaned = "\n".join(lines).strip()

    return cleaned


def _deduplicate_citations(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicates citations and retains only unique, distinct excerpts."""
    seen_tokens = set()
    unique_sources = []
    for s in sources:
        excerpt = str(s.get("excerpt") or "").strip()
        tokens = " ".join(re.findall(r"[a-zA-Z0-9]+", excerpt.lower()))
        if len(tokens) >= 8 and tokens not in seen_tokens:
            seen_tokens.add(tokens)
            unique_sources.append(s)
        elif not tokens and s not in unique_sources:
            unique_sources.append(s)
    # Return at most 2 clean distinct citations to prevent repetitive citation blocks
    return unique_sources[:2]


async def answer_document_question(
    doc: DocumentDetail,
    question: str,
) -> Dict[str, Any]:
    """
    Answers a question about a specific document using its extracted text.
    Returns a dict with 'answer', 'sources', and 'demo_mode'.

    Guarantees:
    - Direct, concise bulleted facts grounded strictly in document text.
    - Zero chain-of-thought, reasoning steps, or internal commentary.
    - Explicit disclosure if requested facts are absent from the document.
    - Deduplicated exact quotation citations.
    """
    if not doc.pages or not any(p.text.strip() for p in doc.pages if p.text):
        return {
            "answer": "No text has been extracted from this document. Please ensure the PDF contains selectable text.",
            "sources": [],
            "demo_mode": False,
            "error": True,
        }

    qa_mode = (settings.QA_MODE or "baseline").strip().lower()
    retrieval_info: Optional[Dict[str, Any]] = None

    if qa_mode == "retrieval":
        # B1: one-shot clause retrieval (experimental)
        page_context, retrieval_info = await anyio.to_thread.run_sync(_build_retrieval_context, doc, question)
        context_note = (
            "The document text below consists of the passages retrieved from the document as most relevant "
            "to the question; it is not the full document.\n\n"
        )
    else:
        # Original behaviour: full document context
        page_context = _build_page_context(doc)
        context_note = ""
    page_count = doc.page_count or len(doc.pages)

    system_prompt = (
        "You are an expert legal document analyst. Answer the user's question using ONLY the provided document text.\n\n"
        + context_note +
        "STRICT ANSWER RULES:\n"
        "1. Be direct, factual, and concise. Format the core terms as clear bullet points.\n"
        "2. Include exact details (e.g. monetary sums, deadlines, percentages, notice periods).\n"
        "3. NEVER narrate your reasoning, thought process, or instructions. Never say 'We need to extract' or 'Now checking'.\n"
        "4. Do NOT repeat quotes or facts across the answer.\n"
        "5. If the document text does not contain the answer, state clearly: 'The provided document does not contain information regarding [topic].'\n"
        f"6. The document contains {page_count} page(s). Citing page numbers must be between 1 and {page_count}.\n"
        "7. Output ONLY a valid JSON object matching the required schema."
    )

    prompt = f"""Document Text:
{page_context}

Question: {question}

Respond with ONLY valid JSON in this exact structure:
{{
  "answer": "A concise overview followed by bullet points of the relevant terms",
  "sources": [
    {{
      "page": 1,
      "excerpt": "One exact sentence or excerpt quoted verbatim from the document"
    }}
  ]
}}"""

    try:
        response_text = await ollama_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            think=False,
            format="json",
            options={"num_predict": 512, "temperature": 0.1}
        )
    except TimeoutError:
        raise
    except Exception as e:
        logger.error("Ollama chat generation failed: %s", e)
        raise RuntimeError(f"AI chat failed: {str(e)}") from e

    # Parse JSON response with fallback repairs
    parsed: Optional[Dict[str, Any]] = None
    first_brace = response_text.find("{")
    if first_brace != -1:
        candidate_json = response_text[first_brace:].strip()
        try:
            parsed = json.loads(candidate_json)
        except json.JSONDecodeError:
            # Try repairing truncated JSON by closing open arrays and objects
            for suffix in [']}', '"]}', '"}', '}']:
                try:
                    parsed = json.loads(candidate_json + suffix)
                    break
                except Exception:
                    pass

    answer = ""
    sources: List[Dict[str, Any]] = []

    if parsed and isinstance(parsed, dict):
        if isinstance(parsed.get("answer"), str):
            answer = parsed["answer"].strip()
        if isinstance(parsed.get("sources"), list):
            for s in parsed["sources"]:
                if isinstance(s, dict) and "page" in s:
                    sources.append({
                        "page": int(s["page"]) if s.get("page") is not None else None,
                        "excerpt": str(s.get("excerpt", "")).strip(),
                    })
    else:
        # Fallback: clean raw text if model output text directly without JSON wrappers
        clean_raw = re.sub(r"^```(?:json)?\s*", "", response_text.strip(), flags=re.I)
        clean_raw = re.sub(r"\s*```$", "", clean_raw).strip()
        answer = clean_raw

    # Sanitize answer: strip any reasoning, prompt echoes, and dangling fragments
    answer = _sanitize_chat_answer(answer)
    if not answer:
        answer = "The provided document does not contain explicit provisions addressing this question."

    # Validate citations against document pages and deduplicate
    sources = _validate_page_citations(sources, doc)
    sources = _deduplicate_citations(sources)

    result: Dict[str, Any] = {
        "answer": answer,
        "sources": sources,
        "demo_mode": False,
    }
    if retrieval_info is not None:
        result["qa_mode"] = qa_mode
        result["retrieval"] = retrieval_info
    return result


def _build_retrieval_context(doc: DocumentDetail, question: str) -> tuple:
    """
    B1 context: top-k clauses from the evidence index, best-first.
    Returns (context_string, retrieval_info) where retrieval_info is JSON-safe.
    """
    from app.services.evidence import store as evidence_store
    from app.services.evidence.retriever import retrieve, format_context

    index = evidence_store.get_or_build(doc, with_dense=settings.EVIDENCE_DENSE_ENABLED)
    found = retrieve(index, question)
    formatted = format_context(index, found["hits"])
    info = {
        "components": found["components"],
        "clauses": [
            {
                **h.to_dict(),
                "heading": index.clause(h.clause_id).heading,
                "page_span": index.clause(h.clause_id).page_span,
                "in_context": h.clause_id in formatted["used"],
            }
            for h in found["hits"]
        ],
        "dropped_for_length": formatted["dropped"],
    }
    if not formatted["context"]:
        # Nothing matched at all: fall back to the full document so the answer path still works,
        # and record that the retrieval step found nothing.
        info["fallback"] = "full_document"
        return _build_page_context(doc), info
    return formatted["context"], info
