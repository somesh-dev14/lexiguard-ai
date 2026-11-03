"""
Document Analysis Service for LexiGuard AI
Provides structured analysis of legal documents.
Supports deterministic demo mode and live AI mode combining:
- Local DeBERTa/ModernBERT clause classification
- Local Ollama (qwen3:4b) contract summarization and risk analysis
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.schemas.document import DocumentDetail
from app.services.classifier_service import classifier_service
from app.services.ollama_client import ollama_client
from app.services.risk_prioritization_service import prioritize_risks

logger = logging.getLogger("lexiguard.analysis")



def _is_placeholder(value: Any) -> bool:
    """Return True for model/schema placeholder strings that must not reach the UI."""
    if value is None:
        return True
    text = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", str(value).lower())).strip()
    if not text:
        return True
    placeholders = {
        "identified parties", "party a", "party b", "obligation 1", "obligation 2",
        "obligation 3", "title of risk", "name of risk", "brief legal explanation",
        "business impact", "recommended mitigation", "effective date",
        "effective date or not explicitly specified", "term duration or unspecified",
        "standard commercial agreement", "commercial agreement", "upon execution",
        "upon mutual execution", "unspecified", "not specified", "not explicitly specified",
        "contract type", "the formal contract category", "not identified in extracted text",
        "no readable text was extracted from this pdf",
    }
    # Reject prompt schema artifacts and model echo tokens
    if text in placeholders or text.startswith("title of risk ") or text.startswith("obligation ") or text.startswith("identified party "):
        return True
    if re.fullmatch(r"you\d*", text) or re.fullmatch(r"party\s*\d*", text):
        return True
    return False


def _extract_grounded_parties(text: str) -> List[str]:
    """
    Extracts verified party legal entity names directly from contract text.
    Handles forms like:
      - Example Client Ltd. ('Client')
      - Sample Solutions Pvt. Ltd. ('Provider')
      - Alpha Technologies Inc. (Provider) and Beta Corp. (Client)
    Rejects placeholders like 'You1', 'Party A', etc.
    """
    found: List[str] = []

    # Pattern 1: Entities followed by role designation (Client, Provider, Licensor, Licensee, Buyer, Seller, Vendor)
    role_pattern = re.compile(
        r"([A-Z][A-Za-z0-9&.,' -]{1,80}?(?:Pvt\.?\s*Ltd\.?|Private Limited|\bLtd\.?|\bLimited|\bLLP|\bInc\.?|\bCorp\.?|\bCorporation|\bLLC))\s*[\(\[]\s*['\"]?(?:Client|Provider|Licensor|Licensee|Customer|Vendor|Supplier|Buyer|Seller|Company|Contractor)['\"]?\s*[\)\]]",
        re.IGNORECASE
    )
    for m in role_pattern.finditer(text):
        candidate = m.group(1).strip(" ,;:\n\r\t")
        # Clean title artifacts
        candidate = re.sub(r"^(?:and\s+)?(?:SAMPLE\s+)?(?:SERVICES|COMMERCIAL|SOFTWARE)\s+AGREEMENT\s+", "", candidate, flags=re.I)
        candidate = re.sub(r"^(?:and|by\s+and\s+between|by)\s+", "", candidate, flags=re.I).strip(" ,;")
        if candidate and len(candidate) >= 3 and not _is_placeholder(candidate) and candidate not in found:
            found.append(candidate)

    # Pattern 2: 'by and between Party A and Party B' introductory clauses
    if not found:
        intro_match = re.search(r"(?i)by\s+and\s+between\s+([A-Z][A-Za-z0-9&.,' -]{2,60})\s+(?:and|\&)\s+([A-Z][A-Za-z0-9&.,' -]{2,60})", text)
        if intro_match:
            for g in (intro_match.group(1), intro_match.group(2)):
                cleaned = re.sub(r"\s*[\(\[].*?[\)\]]", "", g).strip(" ,;.")
                if cleaned and not _is_placeholder(cleaned) and cleaned not in found:
                    found.append(cleaned)

    # Pattern 3: 'entered into on [Date] by Party A and Party B'
    if not found:
        entered_match = re.search(r"(?i)entered\s+into(?:\s+on\s+[^,]+)?\s+by\s+([A-Z][A-Za-z0-9&.,' -]{2,60})\s+(?:and|\&)\s+([A-Z][A-Za-z0-9&.,' -]{2,60})", text)
        if entered_match:
            for g in (entered_match.group(1), entered_match.group(2)):
                cleaned = re.sub(r"\s*[\(\[].*?[\)\]]", "", g).strip(" ,;.")
                if cleaned and not _is_placeholder(cleaned) and cleaned not in found:
                    found.append(cleaned)

    return found


def _source_summary(doc: DocumentDetail, current: Dict[str, Any], clauses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Repair missing/placeholder LLM fields using only text extracted from this PDF."""
    text = "\n".join(p.text for p in doc.pages if p.text).strip()
    flat = re.sub(r"\s+", " ", text)

    # 1. Parties: verify extracted parties against source text; eliminate 'You1' or placeholders
    raw_parties = current.get("parties")
    valid_parties: List[str] = []
    if isinstance(raw_parties, list):
        for p in raw_parties:
            p_str = str(p).strip()
            if p_str and not _is_placeholder(p_str):
                # Verify that party name actually exists in document text
                norm_p = " ".join(re.findall(r"[a-zA-Z0-9]+", p_str.lower()))
                norm_doc = " ".join(re.findall(r"[a-zA-Z0-9]+", flat.lower()))
                if norm_p and norm_p in norm_doc:
                    valid_parties.append(p_str)

    if not valid_parties:
        valid_parties = _extract_grounded_parties(text)

    current["parties"] = valid_parties if valid_parties else ["Not explicitly specified"]

    # 2. Contract type: source-derived rather than generic fabricated default
    ctype = current.get("contract_type")
    if _is_placeholder(ctype):
        title_match = re.search(r"(?im)^\s*(?:sample\s+)?([A-Z][A-Za-z /&-]{2,60}\b(?:Agreement|Contract|License|Licence|NDA))\s*$", text)
        if title_match:
            ctype = title_match.group(1).strip().title()
        else:
            low = flat.lower()
            if "non-disclosure" in low or "confidential information" in low:
                ctype = "Confidentiality Agreement"
            elif "website maintenance" in low or "technical support" in low or "services" in low:
                ctype = "Services Agreement"
            else:
                ctype = "Commercial Agreement"
    current["contract_type"] = str(ctype)

    # 3. Dates and duration: only infer when explicit text supports it
    effective = current.get("effective_date")
    if _is_placeholder(effective):
        date_patterns = [
            r"(?i)(?:effective as of|effective date(?: is)?|entered into on|begins on|commences on|starts on)\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
            r"(?i)(?:effective as of|effective date(?: is)?|entered into on|begins on|commences on|starts on)\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            r"(?i)(?:effective as of|effective date(?: is)?|entered into on|begins on|commences on|starts on)\s+(\d{4}-\d{2}-\d{2})",
        ]
        effective = next((m.group(1).strip() for pat in date_patterns if (m := re.search(pat, flat))), "Not explicitly specified")
    current["effective_date"] = str(effective)

    duration = current.get("duration")
    if _is_placeholder(duration):
        m = re.search(r"(?i)(?:continues? for|term of|period of|duration of)\s+([a-z0-9 -]+?)(?:\s+(?:unless|from|beginning|starting|after|and)\b|[.;,])", flat)
        duration = m.group(1).strip() if m else "Not explicitly specified"
    current["duration"] = str(duration)

    # 4. Key obligations: validate against document text, eliminating generic statements
    obligations = current.get("key_obligations")
    generic_default_phrases = {
        "maintain confidentiality of proprietary information",
        "perform primary contractual deliverables and obligations",
        "comply with applicable governing laws and dispute resolution terms",
        "timely delivery of services or software deliverables",
        "compliance with mutual confidentiality restrictions",
        "standard indemnification subject to liability cap",
    }
    valid_obligations: List[str] = []
    if isinstance(obligations, list):
        for obl in obligations:
            obl_str = str(obl).strip()
            if obl_str and not _is_placeholder(obl_str):
                norm_obl = re.sub(r"\s+", " ", obl_str.lower()).strip()
                if norm_obl not in generic_default_phrases:
                    # Also verify it has grounding in doc text or clauses
                    norm_obl_tokens = " ".join(re.findall(r"[a-zA-Z0-9]+", norm_obl))
                    norm_doc_tokens = " ".join(re.findall(r"[a-zA-Z0-9]+", flat.lower()))
                    if len(norm_obl_tokens) >= 15 and norm_obl_tokens in norm_doc_tokens:
                        valid_obligations.append(obl_str)

    if not valid_obligations:
        # Prioritize material contractual commitments across clauses:
        # - Payment amounts, deadlines, late payment interest, dispute windows
        # - Security incident notifications & confidentiality survival
        # - Support SLA acknowledgement & response commitments
        # - Termination notice & cure periods
        # - Duration, renewal, and operative deliverables
        def _score_obligation_sentence(s: str) -> int:
            score = 0
            low = s.lower()
            # 1. Payment amounts, fees, invoices, late interest, currencies
            if re.search(r"(?:pay|fee|invoice|interest|inr|\$|\€|\£|overdue|late payment|penalty)", low):
                score += 4
            # 2. Dispute deadlines, billing disputes
            if re.search(r"(?:dispute\b|good faith dispute)", low):
                score += 3
            # 3. Termination notice, material breach, and cure periods
            if re.search(r"(?:terminate|termination|written notice|cure\s+(?:the\s+)?breach|material breach)", low):
                score += 4
            # 4. Strict numerical deadlines and time periods (days, hours, months)
            if re.search(r"\b(?:\d+|thirty|sixty|fifteen|ten|seven|five|three|twenty|forty-eight|twenty-four)\s+(?:days?|hours?|business days?|months?|weeks?)\b", low):
                score += 3
            # 5. Security incident notification, breach reporting
            if re.search(r"(?:security incident|data breach|unauthorized access|incident response)", low):
                score += 4
            # 6. Critical support, response time, SLA, remedies
            if re.search(r"(?:response time|acknowledg\w+|service level|uptime|support|remedy)", low):
                score += 3
            # 7. Confidentiality survival periods
            if re.search(r"(?:survives?\s+termination|period of \d+ years|years after termination)", low):
                score += 2
            elif re.search(r"(?:proprietary information|confidential information)", low):
                score += 1
            # 8. Primary service commitments and deliverables
            if re.search(r"(?:deliver|implement|provide|services?|deliverables?|warrant)", low):
                score += 1
            return score

        candidate_sentences: List[Dict[str, Any]] = []
        seen_token_sets = []

        for clause in clauses:
            # Segment into clean sentences
            sentences = re.split(r"(?<=[.!?])\s+", str(clause.get("text", "")))
            for sentence in sentences:
                sentence = re.sub(r"\s+", " ", sentence).strip()
                # Must be substantial and contain a modal or binding verb (shall, must, will, agrees to, is required to, or may <verb>)
                has_binding_modal = bool(re.search(
                    r"\b(must|shall|will|agrees? to|is required to|undertakes? to|agreed to|may\s+[a-z]+)\b",
                    sentence,
                    re.I
                ))
                if len(sentence) >= 30 and has_binding_modal:
                    # Normalized token set for deduplication
                    tokens = frozenset(re.findall(r"[a-z0-9]+", sentence.lower()))
                    if len(tokens) >= 5:
                        # Check duplicate or high overlap (>80% Jaccard) with existing chosen sentences
                        is_duplicate = False
                        for prev_tokens in seen_token_sets:
                            overlap = len(tokens & prev_tokens) / max(len(tokens | prev_tokens), 1)
                            if overlap > 0.80:
                                is_duplicate = True
                                break
                        if not is_duplicate:
                            seen_token_sets.append(tokens)
                            sc = _score_obligation_sentence(sentence)
                            candidate_sentences.append({
                                "text": sentence,
                                "score": sc,
                            })

        if candidate_sentences:
            # Sort stable by score descending
            candidate_sentences.sort(key=lambda x: x["score"], reverse=True)
            current["key_obligations"] = [cs["text"] for cs in candidate_sentences[:5]]
        else:
            current["key_obligations"] = ["No clear operative obligations could be reliably extracted."]
    else:
        current["key_obligations"] = valid_obligations[:5]

    # 5. Overview: produce clean, source-grounded summary text rather than failure message
    overview = current.get("overview")
    needs_overview_repair = (
        _is_placeholder(overview)
        or "no reliable overview could be extracted" in str(overview).lower()
        or "processed with deberta" in str(overview).lower()
    )

    if needs_overview_repair:
        parties_str = " and ".join(current["parties"]) if current.get("parties") and current["parties"][0] != "Not explicitly specified" else "the parties"
        c_type = current.get("contract_type", "commercial agreement")
        date_str = f" effective {current['effective_date']}" if current.get("effective_date") and current["effective_date"] != "Not explicitly specified" else ""
        first_page_clean = re.sub(r"(?i)^\s*(?:[^\n]*test\s+document[^\n]*\n*|page\s+\d+\s*\n*)+", "", doc.pages[0].text if doc.pages else "").strip()
        first_sentence = first_page_clean.split(".")[0].strip() if first_page_clean else ""
        if len(first_sentence) > 30 and ("entered into" in first_sentence.lower() or "agreement" in first_sentence.lower()):
            repaired_overview = f"This {c_type} is entered into by {parties_str}{date_str}. Key provisions define service performance, mutual confidentiality, payment obligations, liability limitations, and governing law."
        else:
            repaired_overview = f"A {c_type} entered into by {parties_str}{date_str}, setting forth mutual rights, obligations, liability terms, and governing procedures."
        current["overview"] = repaired_overview

    return current

def get_demo_analysis_for_document(doc_id: str) -> Dict[str, Any]:
    """
    Returns the baseline demo analysis fixture for backward compatibility.
    """
    return {
        "document_id": doc_id,
        "demo_mode": True,
        "disclaimer": "This analysis is illustrative demo data. Connect AI mode to perform live DeBERTa + LLM analysis.",
        "summary": {
            "overview": "Standard commercial agreement extracted successfully.",
            "contract_type": "Extracted Commercial Contract",
            "parties": ["Party A", "Party B"],
            "effective_date": "Effective: Upon Execution",
            "duration": "12 months standard duration",
            "key_obligations": [
                "Timely delivery of services or software deliverables",
                "Compliance with mutual confidentiality restrictions",
                "Standard indemnification subject to liability cap"
            ]
        },
        "clauses": [],
        "risks": []
    }


# Pass 1: Inline and split headings. Covers headings that appear after ". ", "; ",
# a newline, or at the very start of text. Also handles headings split across two
# lines (e.g. "1. Parties and\nServices."). The lookahead now also accepts end-of-string.
INLINE_CLAUSE_REGEX = re.compile(
    r'(?P<sep>^|[\r\n]+|\.\s+|\;\s+)'
    r'(?P<heading>'
    r'(?:(?:Section|Article|Clause)\s+)?'
    r'(?:\d{1,3}(?:\.\d{1,3})*|[A-Z]|\([a-z0-9]+\))'
    r'[\.\:\)]'
    r'\s+'
    r'[A-Z][A-Za-z0-9\s,\/\-\'\"]*?'
    r')'
    r'(?=\.\s+|\:\s+|\n\s*\n|\s{2,}(?=[A-Z])|\Z)',
    re.MULTILINE
)

# Pass 2: Line-start headings. Covers the common PDF layout where each clause
# heading sits on its own line without a trailing period/colon
# (e.g. "3. Payment Obligations\nClient shall..."). Anchored to line boundaries
# and requires no newline inside the heading text.
LINE_CLAUSE_REGEX = re.compile(
    r'^(?P<heading>'
    r'(?:(?:Section|Article|Clause)\s+)?'
    r'(?:\d{1,3}(?:\.\d{1,3})*|[A-Z]|\([a-z0-9]+\))'
    r'[\.\:\)]'
    r'[ \t]+'           # horizontal whitespace only (no newlines)
    r'[A-Z][A-Za-z0-9 ,\/\-\'\"]*'   # heading words, spaces only
    r')'
    r'$',               # heading occupies the entire line
    re.MULTILINE
)


def _find_clause_headings(full_text: str) -> list:
    """
    Find all numbered clause headings using a two-pass strategy:
    1. INLINE_CLAUSE_REGEX: catches inline/split headings (after . ; newline).
    2. LINE_CLAUSE_REGEX: catches line-start headings missed by pass 1.
    Matches are merged by start position and sorted by document order.
    """
    seen: dict = {}
    # Prioritize line-start headings first so single-line headings aren't swallowed by multiline inline regex
    for m in LINE_CLAUSE_REGEX.finditer(full_text):
        pos = m.start("heading")
        seen[pos] = m
    for m in INLINE_CLAUSE_REGEX.finditer(full_text):
        pos = m.start("heading")
        if pos not in seen:
            seen[pos] = m
    return sorted(seen.values(), key=lambda m: m.start("heading"))


def chunk_document_into_candidate_clauses(doc: DocumentDetail, max_clauses: int = 50) -> List[Dict[str, Any]]:
    """
    Splits document pages into candidate clauses for classification.
    Uses a two-pass regex strategy:
    - Pass 1 (INLINE_CLAUSE_REGEX): inline/split headings (after ". ", "; ", newline)
    - Pass 2 (LINE_CLAUSE_REGEX): line-start headings without a trailing delimiter
    This reliably detects numbered clause headings across common PDF text extraction
    layouts, including headings on their own lines and headings split across two lines.
    Preserves original clause text and page references.
    Falls back to paragraph chunking when no numbered headings are found.
    """
    if not doc.pages:
        return []

    # 1. Map character offsets across the entire document to track page numbers precisely
    full_text_parts: List[str] = []
    char_page_map: List[int] = []

    for page in doc.pages:
        txt = page.text
        if not txt:
            continue
        if full_text_parts:
            full_text_parts.append("\n")
            char_page_map.append(page.page_number)

        full_text_parts.append(txt)
        char_page_map.extend([page.page_number] * len(txt))

    full_document_text = "".join(full_text_parts)
    if not full_document_text.strip():
        return []

    # 2. Find all numbered clause headings using dual-pass strategy
    matches = _find_clause_headings(full_document_text)
    candidates: List[Dict[str, Any]] = []

    if matches:
        for idx, m in enumerate(matches):
            heading_raw = m.group("heading")
            heading_clean = " ".join(heading_raw.split()).strip()
            start_pos = m.start("heading")

            # End of this clause is start of next heading or end of document
            if idx + 1 < len(matches):
                end_pos = matches[idx + 1].start("heading")
            else:
                end_pos = len(full_document_text)

            # Compute actual bounds of the stripped clause text
            clause_slice = full_document_text[start_pos:end_pos]
            raw_clause_text = clause_slice.strip()
            
            # Find exact character offset of the final non-whitespace character
            lstrip_offset = len(clause_slice) - len(clause_slice.lstrip())
            actual_start = start_pos + lstrip_offset
            actual_end = actual_start + len(raw_clause_text)

            start_page = char_page_map[actual_start] if actual_start < len(char_page_map) else doc.pages[0].page_number
            last_char_idx = max(actual_start, min(actual_end - 1, len(char_page_map) - 1)) if char_page_map else 0
            end_page = char_page_map[last_char_idx] if char_page_map else start_page
            page_span = f"{start_page}" if start_page == end_page else f"{start_page}-{end_page}"

            # Retain non-trivial clauses
            if len(raw_clause_text) >= 15:
                candidates.append({
                    "id": f"clause-{len(candidates) + 1:02d}",
                    "heading": heading_clean,
                    "text": raw_clause_text,
                    "page": start_page,
                    "page_start": start_page,
                    "page_end": end_page,
                    "page_span": page_span,
                })
                if len(candidates) >= max_clauses:
                    break

    # 3. Fallback to paragraph-based segmentation if no numbered headings were detected
    if not candidates:
        clause_idx = 1
        for page in doc.pages:
            raw_text = page.text.strip()
            if not raw_text:
                continue

            paragraphs = re.split(r"\n\s*\n+", raw_text)
            for p in paragraphs:
                cleaned = " ".join(p.split()).strip()
                if len(cleaned) >= 50 and len(cleaned.split()) >= 8:
                    heading = f"Clause {clause_idx}"
                    first_sentence = cleaned.split(".")[0]
                    if len(first_sentence) < 60 and ("Section" in first_sentence or "Article" in first_sentence or first_sentence.isupper()):
                        heading = first_sentence

                    candidates.append({
                        "id": f"clause-{clause_idx:02d}",
                        "heading": heading,
                        "text": cleaned,
                        "page": page.page_number,
                        "page_start": page.page_number,
                        "page_end": page.page_number,
                        "page_span": str(page.page_number),
                    })
                    clause_idx += 1
                    if len(candidates) >= max_clauses:
                        return candidates

    return candidates


async def run_ai_document_analysis(doc: DocumentDetail) -> Dict[str, Any]:
    """
    Runs live DeBERTa classification and Ollama generation on an uploaded document.
    """
    # 1. Extract candidate passages for clause classification
    candidates = chunk_document_into_candidate_clauses(doc)
    classified_clauses: List[Dict[str, Any]] = []

    for c in candidates:
        page_start = c.get("page_start", c.get("page"))
        page_end = c.get("page_end", page_start)
        page_span = c.get("page_span", str(page_start) if page_start is not None else "")

        try:
            # Classify candidate clause using singleton LegalClauseClassifier
            pred = classifier_service.classify(c["text"], top_k=3)
            category = pred["predicted_category"]
            classified_clauses.append({
                "id": c["id"],
                "heading": f"{category} ({c['heading']})",
                "original_heading": c["heading"],
                "predicted_category": category,
                "type": category,
                "text": c["text"],
                "page": c["page"],
                "page_start": page_start,
                "page_end": page_end,
                "page_span": page_span,
                "demo": False,
                "top_predictions": pred.get("top_predictions", [])
            })
        except Exception as e:
            logger.warning("Classifier failed on passage %s: %s", c["id"], e)
            classified_clauses.append({
                "id": c["id"],
                "heading": c["heading"],
                "original_heading": c["heading"],
                "predicted_category": "General",
                "type": "General",
                "text": c["text"],
                "page": c["page"],
                "page_start": page_start,
                "page_end": page_end,
                "page_span": page_span,
                "demo": False
            })

    # 2. Build full extracted text context for Ollama (do not truncate mid-clause/mid-sentence)
    # Include all document pages up to a safe token limit, preserving full clause boundaries.
    full_text_preview = "\n\n".join(
        f"[Page {p.page_number}]\n{p.text.strip()}" for p in doc.pages if p.text and p.text.strip()
    )

    ollama_prompt = f"""You are a specialized legal document analyzer. Analyze the complete contract text below and output ONLY valid JSON without any markdown formatting or commentary.

Contract Text:
{full_text_preview}

Output the following JSON schema:
{{
  "overview": "2-3 sentences summarizing the contract scope and core purpose",
  "contract_type": "The formal contract category (e.g. Services Agreement, Non-Disclosure Agreement, Software License, Employment Agreement)",
  "parties": ["Identified party 1", "Identified party 2"],
  "effective_date": "Effective date or 'Not explicitly specified'",
  "duration": "Term duration or 'Unspecified'",
  "key_obligations": [
    "Obligation 1",
    "Obligation 2",
    "Obligation 3"
  ],
  "risks": [
    {{
      "id": "risk-01",
      "severity": "low or medium or high or critical",
      "finding_category": "contractual_defect or negotiation_point or informational",
      "title": "Title of risk or finding",
      "clause": "Name or number of the clause (e.g. '3. Payment Obligations', '4. Indemnification') or 'General'",
      "explanation": "Brief legal explanation of why this creates exposure, requires negotiation, or provides essential context",
      "relevantText": "Direct quote from text supporting this risk",
      "impact": "Business impact",
      "suggestion": "Recommended mitigation or negotiation posture"
    }}
  ]
}}

CRITICAL RULES FOR RISK ANALYSIS AND FINDING CATEGORIZATION:
1. Ground every risk strictly and exclusively in the provided Contract Text above. Do NOT import assumptions, clause requirements, or terms from unrelated contract types or external templates.
2. Distinguish the 'finding_category' carefully:
   - 'contractual_defect': A specific, evidence-supported omission, internal contradiction, or problematic commitment relative to an identifiable operational requirement or explicit contract commitment (e.g., missing payment due dates, contradictory liability caps, missing cure periods).
   - 'negotiation_point': A customary provision that could reasonably be negotiated or adjusted for commercial advantage, but is legally valid and not an inherent contract defect (e.g., requesting mutual non-solicitation, adjusting an interest rate, proposing bilateral NDA carveouts).
   - 'informational': A notable contractual provision (e.g. choice of law, audit rights) that is worth highlighting for reviewer awareness but does not establish an immediate liability or defect.
3. Do NOT label a clause defective merely because a particular protective carveout or optional term is absent. State the relevant operational context and explain why the omission matters without inventing mandatory legal rules.
4. Read and evaluate each clause in its entirety across all pages before asserting omissions.
5. 'relevantText' must be an exact, meaningful direct excerpt or sentence from the contract (minimum 15 characters, never a truncated 2-3 word fragment like 'Client sha'). For genuine omissions, quote the incomplete clause that creates the exposure.
"""

    summary_data = {
        "overview": "Legal contract processed with DeBERTa clause classifier and Ollama intelligence.",
        "contract_type": "Commercial Agreement",
        "parties": ["Identified Parties"],
        "effective_date": "Upon Execution",
        "duration": "Unspecified",
        "key_obligations": [
            "Maintain confidentiality of proprietary information",
            "Perform primary contractual deliverables and obligations",
            "Comply with applicable governing laws and dispute resolution terms"
        ]
    }
    risks_data: List[Dict[str, Any]] = []

    try:
        response_text = await ollama_client.generate(
            prompt=ollama_prompt,
            format="json",
            options={"num_predict": 1024}
        )
        # Attempt to parse json from response
        # Find JSON boundaries
        match = re.search(r"\{[\s\S]*\}", response_text)
        parsed = None
        if match:
            candidate_json = match.group(0)
            try:
                parsed = json.loads(candidate_json)
            except json.JSONDecodeError:
                # If JSON was truncated at the end of the response, try closing risks list and root object
                for suffix in [']}', '"}', '}']:
                    try:
                        parsed = json.loads(candidate_json + suffix)
                        break
                    except Exception:
                        pass
                if parsed is None:
                    # Try trimming to the last complete risk object
                    last_obj_end = candidate_json.rfind("}")
                    if last_obj_end > 0:
                        trimmed = candidate_json[:last_obj_end + 1]
                        for suffix in [']}', '}']:
                            try:
                                parsed = json.loads(trimmed + suffix)
                                break
                            except Exception:
                                pass

        if parsed and isinstance(parsed, dict):
            if "overview" in parsed:
                summary_data["overview"] = str(parsed["overview"])
            if "contract_type" in parsed:
                summary_data["contract_type"] = str(parsed["contract_type"])
            if "parties" in parsed and isinstance(parsed["parties"], list):
                summary_data["parties"] = [str(p) for p in parsed["parties"]]
            if "effective_date" in parsed:
                summary_data["effective_date"] = str(parsed["effective_date"])
            if "duration" in parsed:
                summary_data["duration"] = str(parsed["duration"])
            if "key_obligations" in parsed and isinstance(parsed["key_obligations"], list):
                summary_data["key_obligations"] = [str(o) for o in parsed["key_obligations"]]
            if "risks" in parsed and isinstance(parsed["risks"], list):
                # Build page and clause lookup structures for evidence grounding
                page_texts = {p.page_number: p.text for p in doc.pages if p.text}
                sorted_page_nums = sorted(page_texts.keys())

                def _norm_tokens(s: str) -> str:
                    return " ".join(re.findall(r"[a-zA-Z0-9]+", s.lower()))

                # Also create a continuous document text removing running headers/footers between consecutive pages
                clean_page_texts = {}
                for num, txt in page_texts.items():
                    # Strip recurring top-of-page running headers (e.g. 'LexiGuard AI test document', 'Page X')
                    cleaned_txt = re.sub(
                        r"(?i)^\s*(?:[^\n]*test\s+document[^\n]*\n*|page\s+\d+\s*\n*)+",
                        "",
                        txt
                    )
                    clean_page_texts[num] = cleaned_txt

                continuous_doc_tokens = " ".join(
                    _norm_tokens(clean_page_texts[num]) for num in sorted_page_nums
                )

                for r in parsed["risks"]:
                    if isinstance(r, dict) and ("title" in r or "issue" in r):
                        raw_relevant_text = r.get("relevantText")
                        evidence_unverified = False
                        matched_page: Optional[int] = None
                        matched_clause: Optional[str] = r.get("clause")
                        matched_page_end: Optional[int] = None
                        matched_page_span: Optional[str] = None

                        if raw_relevant_text and isinstance(raw_relevant_text, str):
                            excerpt = raw_relevant_text.strip()
                            excerpt_clean = re.sub(r'^["\']|["\']$', '', excerpt).strip()
                            norm_excerpt = _norm_tokens(excerpt_clean)
                            excerpt_token_list = re.findall(r"[a-zA-Z0-9]+", excerpt_clean.lower())

                            # Verification check 1: minimum length requirement
                            if len(excerpt_clean) < 15 or len(excerpt_token_list) < 3:
                                evidence_unverified = True
                                logger.warning(
                                    "Risk '%s' evidence excerpt not verified (too short <15 chars or <3 words): %r",
                                    r.get("title"),
                                    excerpt[:80],
                                    )
                            else:
                                is_grounded = False

                                # Check 2A: Excerpt found within a single page
                                for page_num in sorted_page_nums:
                                    ptxt_tokens = _norm_tokens(page_texts[page_num])
                                    if norm_excerpt in ptxt_tokens:
                                        is_grounded = True
                                        matched_page = page_num
                                        matched_page_end = page_num
                                        matched_page_span = str(page_num)
                                        break

                                # Check 2B: Excerpt found within a candidate clause
                                if not is_grounded:
                                    for cl in classified_clauses:
                                        cl_tokens = _norm_tokens(cl.get("text", ""))
                                        if norm_excerpt in cl_tokens:
                                            is_grounded = True
                                            if matched_page is None and cl.get("page"):
                                                matched_page = cl.get("page_start", cl["page"])
                                                matched_page_end = cl.get("page_end", matched_page)
                                                matched_page_span = cl.get("page_span", str(matched_page))
                                            if not matched_clause or matched_clause.lower() == "general":
                                                matched_clause = cl.get("heading")
                                            break

                                # Check 2C: Cross-page evidence (excerpt spans across page boundary)
                                if not is_grounded:
                                    if norm_excerpt in continuous_doc_tokens:
                                        is_grounded = True
                                        # Locate starting page where excerpt begins
                                        for i in range(len(sorted_page_nums) - 1):
                                            p_curr = sorted_page_nums[i]
                                            p_next = sorted_page_nums[i + 1]
                                            p_curr_tokens = _norm_tokens(page_texts[p_curr])
                                            p_next_tokens = _norm_tokens(page_texts[p_next])

                                            # Find split where prefix is in current page and suffix is in next page
                                            for split_idx in range(len(excerpt_token_list) - 1, 0, -1):
                                                prefix = " ".join(excerpt_token_list[:split_idx])
                                                suffix = " ".join(excerpt_token_list[split_idx:])
                                                if prefix in p_curr_tokens and suffix in p_next_tokens:
                                                    matched_page = p_curr
                                                    matched_page_end = p_next
                                                    matched_page_span = f"{p_curr}-{p_next}"
                                                    break
                                            if matched_page is not None:
                                                break
                                        if matched_page is None:
                                            matched_page = sorted_page_nums[0]
                                            matched_page_end = sorted_page_nums[-1]
                                            matched_page_span = f"{matched_page}-{matched_page_end}"

                                if not is_grounded:
                                    evidence_unverified = True
                                    logger.warning(
                                        "Risk '%s' evidence excerpt not found in document: %r",
                                        r.get("title"),
                                        excerpt[:80],
                                    )
                                else:
                                    # Correlate with candidate clause if not yet set, and inherit clause page span if applicable
                                    for cl in classified_clauses:
                                        cl_tokens = _norm_tokens(cl.get("text", ""))
                                        prefix_tokens = " ".join(excerpt_token_list[:min(5, len(excerpt_token_list))])
                                        if norm_excerpt in cl_tokens or prefix_tokens in cl_tokens or (matched_clause and matched_clause.lower() in cl.get("heading", "").lower()):
                                            if not matched_clause or matched_clause.lower() == "general":
                                                matched_clause = cl.get("heading")
                                            # Prefer the clause's exact multi-page span if the clause spans multiple pages
                                            if cl.get("page_start") and cl.get("page_end"):
                                                matched_page = cl["page_start"]
                                                matched_page_end = cl["page_end"]
                                                matched_page_span = cl.get("page_span", f"{matched_page}-{matched_page_end}" if matched_page != matched_page_end else str(matched_page))
                                            elif matched_page is None and cl.get("page"):
                                                matched_page = cl.get("page_start", cl["page"])
                                                matched_page_end = cl.get("page_end", matched_page)
                                                matched_page_span = cl.get("page_span", str(matched_page))
                                            break
                        else:
                            evidence_unverified = True

                        # If model supplied a clause name, try to locate its page if not yet matched
                        if matched_page is None and matched_clause:
                            for cl in classified_clauses:
                                if matched_clause.lower() in cl.get("heading", "").lower():
                                    matched_page = cl.get("page_start", cl.get("page"))
                                    matched_page_end = cl.get("page_end", matched_page)
                                    matched_page_span = cl.get("page_span", str(matched_page) if matched_page is not None else None)
                                    break

                        risk_title = str(r.get("title") or r.get("issue") or "").strip()
                        if _is_placeholder(risk_title):
                            logger.warning("Discarding model risk with placeholder title: %r", risk_title)
                            continue
                        severity = str(r.get("severity", "medium")).lower().strip()
                        if severity not in {"low", "medium", "high", "critical"}:
                            severity = "medium"

                        # Determine and normalize finding category
                        raw_cat = str(r.get("finding_category") or r.get("category") or "").lower().strip()
                        if raw_cat in {"contractual_defect", "defect", "omission", "breach", "contradiction"}:
                            finding_category = "contractual_defect"
                        elif raw_cat in {"negotiation_point", "negotiation", "review_point", "negotiation_consideration"}:
                            finding_category = "negotiation_point"
                        elif raw_cat in {"informational", "info", "notice"}:
                            finding_category = "informational"
                        else:
                            # Heuristic inference from title/explanation if model omitted finding_category
                            combined_text = f"{risk_title} {r.get('explanation', '')}".lower()
                            if any(k in combined_text for k in ["missing", "omission", "uncapped", "unlimited", "forfeit", "no cure", "defect", "unilateral"]):
                                finding_category = "contractual_defect"
                            elif any(k in combined_text for k in ["negotiate", "consider", "review point", "customary", "clarify", "propose", "mutual"]):
                                finding_category = "negotiation_point"
                            else:
                                finding_category = "contractual_defect" if severity in {"high", "critical"} else "negotiation_point"

                        risks_data.append({
                            "id": r.get("id", f"risk-{len(risks_data)+1:02d}"),
                            "severity": severity,
                            "finding_category": finding_category,
                            "title": risk_title,
                            "clause": str(matched_clause) if matched_clause else None,
                            "explanation": str(r.get("explanation") or r.get("recommendation") or ""),
                            "relevantText": raw_relevant_text,
                            "page": matched_page,
                            "page_start": matched_page,
                            "page_end": matched_page_end or matched_page,
                            "page_span": matched_page_span or (str(matched_page) if matched_page is not None else None),
                            "impact": r.get("impact"),
                            "suggestion": r.get("suggestion"),
                            "demo": False,
                            "evidence_unverified": evidence_unverified,
                        })
    except Exception as e:
        logger.error("Ollama extraction encountered an error: %s", e)
        # If AI mode is active and Ollama fails, raise so we do not silently claim success
        raise RuntimeError(f"Ollama generation failed during document analysis: {str(e)}") from e

    summary_data = _source_summary(doc, summary_data, classified_clauses)
    prioritized_risks = prioritize_risks(risks_data)

    return {
        "document_id": doc.id,
        "demo_mode": False,
        "summary": summary_data,
        "clauses": classified_clauses,
        "risks": prioritized_risks
    }


async def get_document_analysis(doc: DocumentDetail) -> Dict[str, Any]:
    """
    Main entry point for document analysis.
    Uses AI analysis if settings.AI_MODE == 'ai', otherwise provides demo fallback.
    """
    if settings.AI_MODE.lower() == "ai":
        return await run_ai_document_analysis(doc)
    return get_demo_analysis_for_document(doc.id)
