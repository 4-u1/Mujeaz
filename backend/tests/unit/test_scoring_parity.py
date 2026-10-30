"""Python scoring must reproduce every vector produced by the TypeScript reference."""

import json
from pathlib import Path

import pytest

from app.scoring.scoring import (
    compute_overall,
    compute_revenue_risk,
    denial_risk,
    evidence_score,
    js_round,
    readiness_label,
    rule_score,
)

VECTORS = json.loads((Path(__file__).resolve().parents[3] / "shared" / "scoring_vectors.json").read_text())


def test_vector_file_is_substantial() -> None:
    assert VECTORS["count"] == len(VECTORS["vectors"]) >= 200


@pytest.mark.parametrize("i", range(len(VECTORS["vectors"])))
def test_parity(i: int) -> None:
    v = VECTORS["vectors"][i]
    inp, out = v["input"], v["output"]
    overall = compute_overall(inp["components"], has_failed_rule="FAILED" in inp["rules"])
    risk = denial_risk(overall.overall_score, inp["rules"])
    rr = compute_revenue_risk(inp["financialValue"], risk, inp["evidence"])
    assert rule_score(inp["rules"]) == out["ruleScore"]
    assert evidence_score(inp["evidence"]) == out["evidenceScore"]
    assert overall.overall_score == out["overall"]["overallScore"]
    assert overall.gate_applied == out["overall"]["gateApplied"]
    assert readiness_label(overall.overall_score)[0] == out["label"]
    assert risk == out["denialRisk"]
    assert rr.financial_value == out["revenueRisk"]["financialValue"]
    assert rr.denial_risk_percentage == out["revenueRisk"]["denialRiskPercentage"]
    assert rr.revenue_at_risk == out["revenueRisk"]["revenueAtRisk"]
    assert rr.recoverable_value == out["revenueRisk"]["recoverableValue"]
    assert rr.priority == out["revenueRisk"]["priority"]


def test_js_round_matches_javascript_half_up() -> None:
    assert [js_round(x) for x in (0.5, 1.5, 2.5, -0.5, 69.5)] == [1, 2, 3, 0, 70]


def test_gates() -> None:
    full = dict.fromkeys(
        ("clinicalEvidence", "policyMatch", "documentation", "codingIntegrity", "requiredAttachments",
         "administrativeCompleteness"), 100)
    assert compute_overall(full, has_failed_rule=False).overall_score == 100
    failed = compute_overall(full, has_failed_rule=True)
    assert (failed.overall_score, failed.gate_applied) == (60, "FAILED_MANDATORY_RULE")
    bad_coding = compute_overall({**full, "codingIntegrity": 40}, has_failed_rule=True)
    assert (bad_coding.overall_score, bad_coding.gate_applied) == (50, "INVALID_CODING")


def test_mri_example_from_readme() -> None:
    comps = {"clinicalEvidence": 98, "policyMatch": 96, "documentation": 97, "codingIntegrity": 100,
             "requiredAttachments": 99, "administrativeCompleteness": 100}
    assert compute_overall(comps, has_failed_rule=False).overall_score == 98
    rr = compute_revenue_risk(2800, 78, ["MISSING"])
    assert (rr.revenue_at_risk, rr.recoverable_value, rr.priority) == (2184, 0, "HIGH")
