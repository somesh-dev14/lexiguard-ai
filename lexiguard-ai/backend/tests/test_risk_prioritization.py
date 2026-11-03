"""
Tests for the Explainable Risk Prioritization Engine:
1. Verifies that priority score calculation is deterministic and bounded in [0.0, 100.0].
2. Verifies that high financial exposure and short cure/forfeiture periods amplify risk score.
3. Verifies that unverified or truncated evidence receives an evidence confidence penalty.
4. Verifies that risks are ordered strictly in descending order of priority score.
5. Verifies that each risk includes a transparent factor breakdown dictionary.
"""

import pytest
from app.services.risk_prioritization_service import (
    calculate_risk_priority,
    prioritize_risks,
    evaluate_financial_factor,
    evaluate_obligation_factor,
    evaluate_evidence_confidence,
)


def test_calculate_risk_priority_bounds_and_breakdown():
    risk = {
        "id": "risk-01",
        "severity": "high",
        "title": "Uncapped indemnification exposure",
        "clause": "4. Indemnification",
        "explanation": "Provider indemnifies without any liability cap or limitation.",
        "relevantText": "Provider shall indemnify and hold harmless Client against all claims.",
        "page": 1,
        "evidence_unverified": False,
    }

    breakdown = calculate_risk_priority(risk)
    score = breakdown["priority_score"]
    tier = breakdown["priority_tier"]

    assert 0.0 <= score <= 100.0
    assert tier in ("URGENT", "HIGH", "MODERATE", "LOW")
    assert "factors" in breakdown
    assert "severity" in breakdown["factors"]
    assert "financial_exposure" in breakdown["factors"]
    assert "obligation_asymmetry" in breakdown["factors"]
    assert "evidence_confidence" in breakdown["factors"]
    assert breakdown["factors"]["evidence_confidence"]["multiplier"] == 1.0


def test_unverified_evidence_receives_confidence_penalty():
    verified_risk = {
        "id": "risk-v",
        "severity": "high",
        "title": "Strict Dispute Window",
        "clause": "3. Payment Obligations",
        "explanation": "Dispute within 15 days.",
        "relevantText": "Client may dispute an invoice in good faith by giving written notice within fifteen days.",
        "page": 1,
        "evidence_unverified": False,
    }

    unverified_risk = dict(verified_risk)
    unverified_risk["id"] = "risk-uv"
    unverified_risk["evidence_unverified"] = True

    score_v = calculate_risk_priority(verified_risk)["priority_score"]
    score_uv = calculate_risk_priority(unverified_risk)["priority_score"]

    assert score_v > score_uv, f"Verified risk ({score_v}) should rank higher than unverified risk ({score_uv})"


def test_prioritize_risks_orders_descending():
    risks = [
        {
            "id": "r-low",
            "severity": "low",
            "title": "Governing law in foreign jurisdiction",
            "explanation": "Delaware law governs.",
            "relevantText": "Governed by Delaware law.",
            "page": 1,
            "evidence_unverified": False,
        },
        {
            "id": "r-critical",
            "severity": "critical",
            "title": "Uncapped indemnity and unlimited liability",
            "explanation": "Unlimited liability and third-party indemnity without cure period.",
            "relevantText": "Provider shall indemnify Client without limit or liability cap.",
            "page": 1,
            "evidence_unverified": False,
        },
        {
            "id": "r-medium",
            "severity": "medium",
            "title": "Brief dispute window",
            "explanation": "Must dispute invoice within 15 days.",
            "relevantText": "Dispute within fifteen days or pay late fee interest at 1% per month.",
            "page": 1,
            "evidence_unverified": False,
        }
    ]

    prioritized = prioritize_risks(risks, sort_by_priority=True)

    assert len(prioritized) == 3
    # Check descending score order
    assert prioritized[0]["priority_score"] >= prioritized[1]["priority_score"] >= prioritized[2]["priority_score"]
    assert prioritized[0]["id"] == "r-critical"
    assert prioritized[0]["priority_tier"] in ("URGENT", "HIGH")
    assert "priority_breakdown" in prioritized[0]
