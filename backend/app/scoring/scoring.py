"""Python port of shared/scoring.ts (PRD §8).

Parity with the TypeScript reference is enforced by shared/scoring_vectors.json,
which both test suites must reproduce exactly. JavaScript's Math.round rounds
halves toward +infinity, so ``js_round`` is used instead of Python's round().
"""

import math
from dataclasses import dataclass
from typing import Literal

RuleStatus = Literal["PASSED", "WARNING", "FAILED"]
EvidenceStatus = Literal["FOUND", "PARTIAL", "MISSING"]
Priority = Literal["HIGH", "MEDIUM", "LOW"]

COMPONENTS: tuple[str, ...] = (
    "clinicalEvidence",
    "policyMatch",
    "documentation",
    "codingIntegrity",
    "requiredAttachments",
    "administrativeCompleteness",
)
READINESS_WEIGHTS: dict[str, float] = {
    "clinicalEvidence": 0.3,
    "policyMatch": 0.25,
    "documentation": 0.15,
    "codingIntegrity": 0.15,
    "requiredAttachments": 0.1,
    "administrativeCompleteness": 0.05,
}
GATE_FAILED_RULE_CAP = 60
GATE_INVALID_CODING_CAP = 50
INVALID_CODING_THRESHOLD = 70


def js_round(x: float) -> int:
    return math.floor(x + 0.5)


def _clamp(n: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, n))


def _safe(n: object) -> float:
    if isinstance(n, bool) or not isinstance(n, int | float) or not math.isfinite(n):
        return 0.0
    return _clamp(float(n), 0, 100)


def rule_score(statuses: list[RuleStatus]) -> int | None:
    if not statuses:
        return None
    pts = 0.0
    for s in statuses:
        pts += 1 if s == "PASSED" else 0.5 if s == "WARNING" else 0
    return js_round((pts / len(statuses)) * 100)


def evidence_score(statuses: list[EvidenceStatus]) -> int | None:
    if not statuses:
        return None
    pts = 0.0
    for s in statuses:
        pts += 1 if s == "FOUND" else 0.5 if s == "PARTIAL" else 0
    return js_round((pts / len(statuses)) * 100)


def readiness_label(score: float) -> tuple[str, str]:
    if score >= 90:
        return "Decision Ready", "جاهز للقرار"
    if score >= 70:
        return "Action Recommended", "يُنصح بإجراء قبل الإرسال"
    return "Action Required", "يتطلب إجراء قبل الإرسال"


@dataclass(frozen=True)
class Overall:
    overall_score: int
    gate_applied: str | None


def compute_overall(components: dict[str, float], *, has_failed_rule: bool) -> Overall:
    score = 0.0
    for k in COMPONENTS:
        score += _safe(components.get(k)) * READINESS_WEIGHTS[k]
    rounded = js_round(score)
    gate: str | None = None
    if _safe(components.get("codingIntegrity")) < INVALID_CODING_THRESHOLD and rounded > GATE_INVALID_CODING_CAP:
        rounded = GATE_INVALID_CODING_CAP
        gate = "INVALID_CODING"
    elif has_failed_rule and rounded > GATE_FAILED_RULE_CAP:
        rounded = GATE_FAILED_RULE_CAP
        gate = "FAILED_MANDATORY_RULE"
    return Overall(rounded, gate)


def denial_risk(overall_score: float, rules: list[RuleStatus]) -> int:
    p = 100 - overall_score
    if "FAILED" in rules:
        p = max(p, 85)
    elif "WARNING" in rules:
        p = max(p, 50)
    return int(_clamp(js_round(p), 2, 98))


@dataclass(frozen=True)
class RevenueRisk:
    financial_value: int
    denial_risk_percentage: float
    revenue_at_risk: int
    recoverable_value: int
    priority: Priority


def compute_revenue_risk(
    financial_value: float, denial_risk_percentage: float, evidence: list[EvidenceStatus]
) -> RevenueRisk:
    value = max(0, js_round(financial_value or 0))
    p = _clamp(denial_risk_percentage, 0, 100)
    at_risk = js_round(value * (p / 100))
    support = (evidence_score(evidence) or 0) / 100
    recoverable = js_round(at_risk * support)
    priority: Priority = "HIGH" if p >= 60 or at_risk >= 10000 else "MEDIUM" if p >= 30 else "LOW"
    return RevenueRisk(value, p, at_risk, recoverable, priority)
