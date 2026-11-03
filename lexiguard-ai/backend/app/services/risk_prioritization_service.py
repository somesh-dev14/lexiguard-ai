"""
Explainable Risk Prioritization Engine for LexiGuard AI.

Provides deterministic, formulaic, and explainable multi-factor scoring
and ranking of identified contractual risks.

Factors:
1. Base Severity (S): Qualitative baseline (critical=1.0, high=0.75, medium=0.5, low=0.25).
2. Evidence Grounding & Verification (E): Confidence multiplier based on exact text grounding,
   cross-page attribution, and token length (verified=1.0, unverified=0.4, missing=0.2).
3. Financial Exposure (F): Detected exposure level (uncapped liability/indemnity, monetary penalties,
   interest accrual, or fixed liability caps).
4. Obligation Asymmetry & Enforceability (O): Unilateral vs mutual burden, strict forfeiture windows,
   cure period deficiencies.

Composite Score Formula:
   Raw Score = (w_s * S + w_f * F + w_o * O) * E
   Normalized Score = round(Raw Score * 100, 1)  [Range: 0.0 - 100.0]

Each scored risk includes an explainable breakdown dictionary detailing factor values,
weights applied, and natural language scoring rationale.
"""

from typing import Dict, Any, List, Optional
import re

# Standard weights summing to 1.0
WEIGHT_SEVERITY = 0.45
WEIGHT_FINANCIAL = 0.30
WEIGHT_OBLIGATION = 0.25

SEVERITY_WEIGHTS = {
    "critical": 1.0,
    "high": 0.75,
    "medium": 0.50,
    "low": 0.25
}

# Regex patterns for detecting financial exposure signals
FINANCIAL_PATTERNS = [
    (re.compile(r"(uncapped|unlimited liability|no liability cap|without limit)", re.IGNORECASE), 1.0, "Uncapped or unlimited financial liability detected"),
    (re.compile(r"(indemnif\w+|hold harmless|defense and indemn)", re.IGNORECASE), 0.85, "Third-party indemnification exposure detected"),
    (re.compile(r"(liquidated damages|penalty|forfeit\w+|interest at \d+|late fee)", re.IGNORECASE), 0.70, "Explicit liquidated damages, penalty, or interest accrual detected"),
    (re.compile(r"(fee|inr|\$|\€|\£|payment|invoice|aggregate liability|cap)", re.IGNORECASE), 0.50, "Direct monetary consideration or capped financial terms"),
]

# Regex patterns for detecting obligation asymmetry and enforceability
ASYMMETRY_PATTERNS = [
    (re.compile(r"(sole discretion|unilateral\w*|client shall solely|provider shall solely|without right to cure)", re.IGNORECASE), 0.90, "Unilateral obligation or lack of cure rights"),
    (re.compile(r"(within (?:15|fifteen|7|seven|5|five|10|ten|3|three) days|strict deadline|time is of the essence)", re.IGNORECASE), 0.75, "Strict procedural forfeiture or abbreviated notice window"),
    (re.compile(r"(material breach|immediate termination|cure the breach within)", re.IGNORECASE), 0.60, "Termination for breach or conditional cure mechanism"),
    (re.compile(r"(exclusive remedy|waive\w* (?:any|all) right|disclaim\w*)", re.IGNORECASE), 0.70, "Waiver of remedies or rights disclaimer"),
]


def evaluate_financial_factor(risk: Dict[str, Any]) -> tuple[float, str]:
    """Evaluates financial risk exposure from title, explanation, impact, and relevant text."""
    combined_text = " ".join([
        str(risk.get("title") or ""),
        str(risk.get("explanation") or ""),
        str(risk.get("impact") or ""),
        str(risk.get("relevantText") or ""),
        str(risk.get("clause") or "")
    ])

    for pattern, score, reason in FINANCIAL_PATTERNS:
        if pattern.search(combined_text):
            return score, reason

    return 0.20, "Standard operational terms without heightened monetary liability"


def evaluate_obligation_factor(risk: Dict[str, Any]) -> tuple[float, str]:
    """Evaluates obligation asymmetry and cure vulnerability."""
    combined_text = " ".join([
        str(risk.get("title") or ""),
        str(risk.get("explanation") or ""),
        str(risk.get("impact") or ""),
        str(risk.get("relevantText") or ""),
        str(risk.get("clause") or "")
    ])

    for pattern, score, reason in ASYMMETRY_PATTERNS:
        if pattern.search(combined_text):
            return score, reason

    return 0.25, "Bilateral or standard operational obligation structure"


def evaluate_evidence_confidence(risk: Dict[str, Any]) -> tuple[float, str]:
    """
    Evaluates evidence grounding confidence multiplier.
    Verified exact cross-page/single-page quotes get 1.0.
    Unverified or short excerpts get downgraded.
    """
    if risk.get("evidence_unverified") is True:
        relevant_text = str(risk.get("relevantText") or "").strip()
        if not relevant_text:
            return 0.30, "No supporting contractual evidence excerpt supplied"
        if len(relevant_text) < 15:
            return 0.40, f"Evidence excerpt too short or truncated ('{relevant_text}')"
        return 0.50, "Evidence excerpt could not be verified in the source contract text"

    relevant_text = str(risk.get("relevantText") or "").strip()
    if relevant_text and len(relevant_text) >= 15:
        page_ref = risk.get("page")
        if page_ref:
            return 1.0, f"Verified exact source text quotation grounded to Page {page_ref}"
        return 0.90, "Verified source text quotation (unpaginated match)"

    return 0.60, "Contextual finding without direct quoted evidence"


def calculate_risk_priority(risk: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculates a deterministic multi-factor priority score and explainable breakdown for a risk.
    """
    # 1. Base Severity (S)
    sev_str = str(risk.get("severity", "medium")).lower()
    sev_score = SEVERITY_WEIGHTS.get(sev_str, 0.50)

    # 2. Financial Exposure (F)
    fin_score, fin_reason = evaluate_financial_factor(risk)

    # 3. Obligation Asymmetry (O)
    obl_score, obl_reason = evaluate_obligation_factor(risk)

    # 4. Evidence Confidence (E)
    evi_mult, evi_reason = evaluate_evidence_confidence(risk)

    # Composite formula
    weighted_sum = (
        (WEIGHT_SEVERITY * sev_score) +
        (WEIGHT_FINANCIAL * fin_score) +
        (WEIGHT_OBLIGATION * obl_score)
    )
    raw_composite = weighted_sum * evi_mult
    priority_score = round(raw_composite * 100.0, 1)

    # Categorical priority tier
    if priority_score >= 70.0:
        priority_tier = "URGENT"
    elif priority_score >= 45.0:
        priority_tier = "HIGH"
    elif priority_score >= 25.0:
        priority_tier = "MODERATE"
    else:
        priority_tier = "LOW"

    breakdown = {
        "priority_score": priority_score,
        "priority_tier": priority_tier,
        "factors": {
            "severity": {
                "weight": WEIGHT_SEVERITY,
                "score": sev_score,
                "rating": sev_str
            },
            "financial_exposure": {
                "weight": WEIGHT_FINANCIAL,
                "score": fin_score,
                "rationale": fin_reason
            },
            "obligation_asymmetry": {
                "weight": WEIGHT_OBLIGATION,
                "score": obl_score,
                "rationale": obl_reason
            },
            "evidence_confidence": {
                "multiplier": evi_mult,
                "rationale": evi_reason
            }
        },
        "formula": "Score = 100 * ((0.45 * Sev + 0.30 * Fin + 0.25 * Obl) * EvidenceMult)"
    }

    return breakdown


def prioritize_risks(risks: List[Dict[str, Any]], sort_by_priority: bool = False) -> List[Dict[str, Any]]:
    """
    Enriches each risk with priority_score, priority_tier, and priority_breakdown.
    If sort_by_priority is True, sorts risks in descending order of priority_score.
    Otherwise preserves original document order while attaching prioritization metadata.
    """
    enriched_risks = []
    for r in risks:
        r_copy = dict(r)
        breakdown = calculate_risk_priority(r_copy)
        r_copy["priority_score"] = breakdown["priority_score"]
        r_copy["priority_tier"] = breakdown["priority_tier"]
        r_copy["priority_breakdown"] = breakdown
        enriched_risks.append(r_copy)

    if sort_by_priority:
        # Deterministic sort: highest priority_score first, ties broken by original id
        enriched_risks.sort(key=lambda x: (-x["priority_score"], str(x.get("id", ""))))

    return enriched_risks
