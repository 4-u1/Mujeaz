"""A5 — readiness components from agent results, then the shared deterministic formulas (PRD §8)."""

from dataclasses import dataclass, field
from typing import Any

from app.agents.types import EvidenceResult, Fact, PatientRecord, RuleResult
from app.scoring.scoring import (
    COMPONENTS,
    READINESS_WEIGHTS,
    RevenueRisk,
    compute_overall,
    compute_revenue_risk,
    denial_risk,
    evidence_score,
    readiness_label,
    rule_score,
)

INDEX_DOCUMENTATION = ("symptom_duration", "exam_slr", "requested_service")
LABEL_TEXT = {"symptom_duration": ("symptom duration", "مدة الأعراض"), "exam_slr": ("examination finding", "نتيجة الفحص"),
              "requested_service": ("requested service", "الخدمة المطلوبة")}
COMPONENT_TEXT = {
    "clinicalEvidence": ("Clinical evidence", "الأدلة السريرية"),
    "policyMatch": ("Policy rules", "قواعد السياسة"),
    "documentation": ("Ordering-note documentation", "توثيق ملاحظة الطلب"),
    "codingIntegrity": ("Coding integrity", "سلامة الترميز"),
    "requiredAttachments": ("Required attachments", "المرفقات المطلوبة"),
    "administrativeCompleteness": ("Administrative completeness", "الاكتمال الإداري"),
}
GATE_TEXT = {
    "INVALID_CODING": ("Capped at 50: the diagnosis is not compatible with the service.",
                       "سقف 50: التشخيص غير متوافق مع الخدمة."),
    "FAILED_MANDATORY_RULE": ("Capped at 60: a mandatory policy rule failed.", "سقف 60: قاعدة إلزامية غير مستوفاة."),
}


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
    explanation: dict[str, Any] = field(default_factory=dict)


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
    explanation = explain(comps, overall.overall_score, overall.gate_applied,
                          _causes(record, facts, evidence, rules, index_labels, exempt))
    return Readiness(comps, overall.overall_score, overall.gate_applied, en, ar, p, rr, warning, warning_ar,
                     explanation)


def _causes(record: PatientRecord, facts: list[Fact], evidence: dict[str, EvidenceResult], rules: list[RuleResult],
            index_labels: set[str], exempt: bool) -> dict[str, list[tuple[str, str]]]:
    c: dict[str, list[tuple[str, str]]] = {k: [] for k in COMPONENTS}
    if exempt:
        c["clinicalEvidence"].append(("Requirement waived: red-flag findings documented.", "الشرط مُعفى: توجد مؤشرات خطيرة موثقة."))
    for e in evidence.values():
        if e.status != "FOUND" and not exempt:
            c["clinicalEvidence"].append((f"{e.requirement_id}: {e.status} — {e.reason}",
                                          f"{e.requirement_id}: {e.status} — {e.reason_ar}"))
            c["requiredAttachments"].append((f"No complete proof to attach for {e.requirement_id}.",
                                             f"لا يوجد إثبات مكتمل لإرفاقه لـ {e.requirement_id}."))
    for r in rules:
        if r.outcome != "PASSED":
            c["policyMatch"].append((f"{r.code} {r.outcome}: {r.reason}", f"{r.code} {r.outcome}: {r.reason_ar}"))
            if "diagnosis" in r.rule_id:
                c["codingIntegrity"].append((f"Diagnosis {record.diagnosis_code} fails {r.code}.",
                                             f"التشخيص {record.diagnosis_code} لا يستوفي {r.code}."))
    for lab in INDEX_DOCUMENTATION:
        if lab not in index_labels:
            en, ar = LABEL_TEXT[lab]
            c["documentation"].append((f"The ordering note does not state the {en}.", f"ملاحظة الطلب لا تذكر {ar}."))
    if not (record.diagnosis_code and record.service_code and record.payer_code):
        c["administrativeCompleteness"].append(("Diagnosis, service or payer is missing.", "التشخيص أو الخدمة أو الجهة ناقصة."))
    return c


def explain(components: dict[str, int], overall: int, gate: str | None,
            causes: dict[str, list[tuple[str, str]]]) -> dict[str, Any]:
    """Per-point explanation built from the same numbers as the score.

    Invariant (tested on every case): js_round(sum(contribution)) - gateReduction == overall.
    """
    from app.scoring.scoring import js_round

    rows = []
    for k in COMPONENTS:
        w = READINESS_WEIGHTS[k]
        score = components[k]
        en, ar = COMPONENT_TEXT[k]
        rows.append({"component": k, "label": en, "labelAr": ar, "score": score, "weight": w,
                     "contribution": round(score * w, 4), "pointsLost": round((100 - score) * w, 4),
                     "causes": [x[0] for x in causes.get(k, [])] if score < 100 else [],
                     "causesAr": [x[1] for x in causes.get(k, [])] if score < 100 else []})
    raw = js_round(sum(r["contribution"] for r in rows))
    out: dict[str, Any] = {"components": rows, "weightedTotal": raw, "gate": gate,
                           "gateReduction": raw - overall, "overall": overall}
    if gate:
        out["gateText"], out["gateTextAr"] = GATE_TEXT[gate]
    return out
