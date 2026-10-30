"""A5 — readiness components from agent results, then the shared deterministic formulas (PRD §8)."""

from dataclasses import dataclass

from app.agents.types import EvidenceResult, Fact, PatientRecord, RuleResult
from app.scoring.scoring import (
    RevenueRisk,
    compute_overall,
    compute_revenue_risk,
    denial_risk,
    evidence_score,
    readiness_label,
    rule_score,
)

INDEX_DOCUMENTATION = ("symptom_duration", "exam_slr", "requested_service")


@dataclass(frozen=True)
class Readiness:
    components: dict[str, int]
    overall: int
    gate: str | None
    label: str
    label_ar: str
    denial_risk: int
    revenue: RevenueRisk
    warning: str | None
    warning_ar: str | None


def assess(record: PatientRecord, facts: list[Fact], evidence: dict[str, EvidenceResult],
           rules: list[RuleResult], price_sar: float, exempt: bool) -> Readiness:
    ev_statuses = [e.status for e in evidence.values()]
    rule_outcomes = [r.outcome for r in rules]
    index_labels = {f.label for f in facts if record.index_doc_ref is None or f.doc_ref == record.index_doc_ref}
    coding_ok = all(r.outcome == "PASSED" for r in rules if "diagnosis" in r.rule_id)
    r1 = next(iter(evidence.values()), None)
    attachments = 100 if exempt or (r1 and r1.status == "FOUND") else 60 if r1 and r1.status == "PARTIAL" else 30
    comps = {
        "clinicalEvidence": 100 if exempt else (evidence_score(ev_statuses) or 0),
        "policyMatch": rule_score(rule_outcomes) or 0,
        "documentation": round(100 * sum(lab in index_labels for lab in INDEX_DOCUMENTATION) / len(INDEX_DOCUMENTATION)),
        "codingIntegrity": 100 if coding_ok else 40,
        "requiredAttachments": attachments,
        "administrativeCompleteness": 100 if record.diagnosis_code and record.service_code and record.payer_code else 60,
    }
    overall = compute_overall({k: float(v) for k, v in comps.items()},
                              has_failed_rule=any(r.outcome == "FAILED" and r.mandatory for r in rules))
    en, ar = readiness_label(overall.overall_score)
    p = denial_risk(overall.overall_score, rule_outcomes)
    rr = compute_revenue_risk(price_sar, p, ev_statuses)
    failing = [r for r in rules if r.outcome != "PASSED"]
    warning = "; ".join(f"{r.code}: {r.reason}" for r in failing) or None
    warning_ar = "؛ ".join(f"{r.code}: {r.reason_ar}" for r in failing) or None
    return Readiness(comps, overall.overall_score, overall.gate_applied, en, ar, p, rr, warning, warning_ar)
