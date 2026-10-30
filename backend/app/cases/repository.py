"""Case queries and the ClaimDigitalTwin view consumed by the frontend.

All queries run on a tenant-scoped connection; RLS limits rows to the caller's
organisation even though queries also filter explicitly where it helps.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import Connection, text

from app.audit.service import list_chains
from app.cases.state_machine import allowed_targets

NOT_ANALYZED: dict[str, Any] = {
    "clinicalEvidence": 0,
    "policyMatch": 0,
    "documentation": 0,
    "codingIntegrity": 0,
    "requiredAttachments": 0,
    "administrativeCompleteness": 0,
    "overallScore": 0,
    "readinessLabel": "Not analyzed yet",
    "readinessLabelAr": "لم يُحلَّل بعد",
}

PENDING_FHIR = {
    "resourceType": "Claim",
    "id": "not-built",
    "status": "draft",
    "patientRef": "",
    "providerRef": "",
    "payerRef": "",
    "diagnosisCodes": [],
    "procedureCodes": [],
    "attachmentsCount": 0,
    "rawJson": '{\n  "note": "The FHIR prior-authorization Claim is built in milestone M4."\n}',
}


def _bilingual(name: str, name_ar: str | None) -> str:
    return f"{name_ar} / {name}" if name_ar else name


def _num(v: Any) -> int | float:
    if v is None:
        return 0
    f = float(v)
    return int(f) if f.is_integer() else f


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


_CASE_SELECT = """
SELECT ar.id, ar.case_number, ar.legacy_id, ar.status, ar.requested_service, ar.requested_service_ar,
       ar.service_code, ar.diagnosis_code, ar.diagnosis_display, ar.financial_value_sar,
       ar.physician_name, ar.specialty, ar.clinical_note, ar.data_source, ar.extra, ar.requested_on,
       p.external_ref AS patient_ref, p.display_name AS patient_name, p.birth_year, p.gender,
       f.name AS facility_name, f.name_ar AS facility_name_ar,
       py.code AS payer_code, py.name AS payer_name, py.name_ar AS payer_name_ar,
       rs.clinical_evidence, rs.policy_match, rs.documentation, rs.coding_integrity,
       rs.required_attachments, rs.administrative_completeness, rs.overall_score, rs.label, rs.label_ar,
       rs.warning, rs.warning_ar, rs.gate_applied,
       rr.financial_value_sar AS rr_value, rr.denial_risk_pct, rr.revenue_at_risk_sar,
       rr.recoverable_value_sar, rr.priority
FROM authorization_requests ar
JOIN patients p ON p.id = ar.patient_id
JOIN payers py ON py.id = ar.payer_id
LEFT JOIN facilities f ON f.id = ar.facility_id
LEFT JOIN LATERAL (
  SELECT * FROM readiness_scores s WHERE s.authorization_request_id = ar.id
  ORDER BY s.computed_at DESC LIMIT 1) rs ON true
LEFT JOIN LATERAL (
  SELECT * FROM revenue_risk r WHERE r.authorization_request_id = ar.id
  ORDER BY r.computed_at DESC LIMIT 1) rr ON true
"""


def list_cases(
    conn: Connection, *, status: str | None = None, q: str | None = None, limit: int = 100, offset: int = 0
) -> list[dict[str, Any]]:
    where: list[str] = ["true"]
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if status:
        where.append("ar.status = :status")
        params["status"] = status
    if q:
        where.append("(ar.case_number ILIKE :q OR ar.requested_service ILIKE :q OR p.external_ref ILIKE :q)")
        params["q"] = f"%{q}%"
    sql = _CASE_SELECT + " WHERE " + " AND ".join(where) + (
        " ORDER BY ar.data_source, ar.requested_on DESC, ar.case_number LIMIT :limit OFFSET :offset"
    )
    rows = conn.execute(text(sql), params).mappings().all()
    return [_summary(r) for r in rows]


def count_cases(conn: Connection) -> int:
    return int(conn.execute(text("SELECT count(*) FROM authorization_requests")).scalar_one())


def _summary(r: Any) -> dict[str, Any]:
    return {
        "id": str(r["id"]),
        "caseNumber": r["case_number"],
        "legacyId": r["legacy_id"],
        "status": r["status"],
        "requestedService": r["requested_service"],
        "payerName": _bilingual(r["payer_name"], r["payer_name_ar"]),
        "patientId": r["patient_ref"],
        "requestedOn": _iso(r["requested_on"]),
        "dataSource": r["data_source"],
        "overallScore": r["overall_score"],
        "revenueAtRisk": _num(r["revenue_at_risk_sar"]) if r["revenue_at_risk_sar"] is not None else None,
    }


def get_case_row(conn: Connection, case_id: str) -> Any:
    return conn.execute(text(_CASE_SELECT + " WHERE ar.id = :id"), {"id": case_id}).mappings().first()


@dataclass
class _Related:
    """Child rows for a batch of cases, keyed by case id. Loaded with one query per table."""

    facts: dict[str, list[Any]] = field(default_factory=dict)
    reqs: dict[str, list[Any]] = field(default_factory=dict)
    evidence: dict[str, list[Any]] = field(default_factory=dict)
    runs: dict[str, list[Any]] = field(default_factory=dict)
    fhir: dict[str, Any] = field(default_factory=dict)
    appeals: dict[str, dict[str, Any]] = field(default_factory=dict)
    audit: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


def _group(rows: Any) -> dict[str, list[Any]]:
    out: dict[str, list[Any]] = defaultdict(list)
    for row in rows:
        out[str(row["case_id"])].append(row)
    return out


def _load_related(conn: Connection, ids: list[str]) -> _Related:
    p = {"ids": ids}
    rel = _Related()
    rel.facts = _group(conn.execute(text(
        "SELECT authorization_request_id AS case_id, id, fact, fact_ar, category, source_label, fact_date, "
        "confidence FROM clinical_facts WHERE authorization_request_id = ANY(CAST(:ids AS uuid[])) "
        "ORDER BY authorization_request_id, ord, created_at"), p).mappings())
    rel.reqs = _group(conn.execute(text(
        "SELECT authorization_request_id AS case_id, id, code, title, title_ar, requirement, requirement_ar, "
        "status, evidence_source FROM authorization_requirements WHERE authorization_request_id = ANY(CAST(:ids AS uuid[])) "
        "ORDER BY authorization_request_id, ord"), p).mappings())
    rel.evidence = _group(conn.execute(text(
        "SELECT authorization_request_id AS case_id, id, requirement, requirement_ar, status, matched_fact, "
        "source_label, evidence_date, confidence FROM authorization_evidence "
        "WHERE authorization_request_id = ANY(CAST(:ids AS uuid[])) ORDER BY authorization_request_id, ord"), p).mappings())
    rel.runs = _group(conn.execute(text(
        "SELECT DISTINCT ON (authorization_request_id, agent_id) authorization_request_id AS case_id, agent_id, "
        "name, name_ar, status, output_summary, output_summary_ar, latency_ms, started_at FROM agent_runs "
        "WHERE authorization_request_id = ANY(CAST(:ids AS uuid[])) ORDER BY authorization_request_id, agent_id, started_at DESC"),
        p).mappings())
    rel.fhir = {str(r["case_id"]): r["payload"] for r in conn.execute(text(
        "SELECT DISTINCT ON (authorization_request_id) authorization_request_id AS case_id, payload "
        "FROM nphies_transactions WHERE authorization_request_id = ANY(CAST(:ids AS uuid[])) "
        "ORDER BY authorization_request_id, created_at DESC"), p).mappings()}
    rel.appeals = _appeal_packages(conn, ids)
    for entry in list_chains(conn, ids):
        rel.audit.setdefault(entry["chain_key"], []).append(entry)
    return rel


def build_twins(conn: Connection, ids: list[str]) -> list[dict[str, Any]]:
    """Full case views for many cases with a constant number of queries (no N+1)."""
    if not ids:
        return []
    rows = {str(r["id"]): r for r in conn.execute(
        text(_CASE_SELECT + " WHERE ar.id = ANY(CAST(:ids AS uuid[]))"), {"ids": ids}).mappings().all()}
    rel = _load_related(conn, ids)
    return [_assemble(rows[i], rel) for i in ids if i in rows]


def build_twin(conn: Connection, case_id: str) -> dict[str, Any] | None:
    twins = build_twins(conn, [case_id])
    return twins[0] if twins else None


def _assemble(r: Any, rel: _Related) -> dict[str, Any]:
    cid = str(r["id"])
    birth_year, req_on = r["birth_year"], r["requested_on"]
    analyzed = r["overall_score"] is not None
    readiness: dict[str, Any] = NOT_ANALYZED.copy() if not analyzed else {
        "clinicalEvidence": r["clinical_evidence"],
        "policyMatch": r["policy_match"],
        "documentation": r["documentation"],
        "codingIntegrity": r["coding_integrity"],
        "requiredAttachments": r["required_attachments"],
        "administrativeCompleteness": r["administrative_completeness"],
        "overallScore": r["overall_score"],
        "readinessLabel": r["label"],
        "readinessLabelAr": r["label_ar"],
    }
    if analyzed and r["warning"]:
        readiness["warningNotice"] = r["warning"]
        readiness["warningNoticeAr"] = r["warning_ar"]

    value = _num(r["financial_value_sar"])
    revenue = {
        "financialValue": _num(r["rr_value"]) if r["rr_value"] is not None else value,
        "denialRiskPercentage": r["denial_risk_pct"] or 0,
        "revenueAtRisk": _num(r["revenue_at_risk_sar"]),
        "recoverableValue": _num(r["recoverable_value_sar"]),
        "priority": r["priority"] or "LOW",
    }

    twin: dict[str, Any] = {
        "id": cid,
        "legacyId": r["legacy_id"],
        "dataSource": r["data_source"],
        "analyzed": analyzed,
        "allowedTransitions": [t.value for t in allowed_targets(r["status"])],
        "claimNumber": r["case_number"],
        "patientName": r["patient_name"],
        "patientId": r["patient_ref"],
        "age": (req_on.year - birth_year) if birth_year and req_on else None,
        "gender": r["gender"],
        "doctorName": r["physician_name"],
        "specialty": r["specialty"],
        "facilityName": _bilingual(r["facility_name"], r["facility_name_ar"]) if r["facility_name"] else "",
        "payerName": _bilingual(r["payer_name"], r["payer_name_ar"]),
        "payerCode": r["payer_code"],
        "requestedService": r["requested_service"],
        "requestedServiceAr": r["requested_service_ar"] or r["requested_service"],
        "cptCode": r["service_code"],
        "icd10Code": r["diagnosis_code"],
        "createdDate": _iso(req_on),
        "status": r["status"],
        "clinicalNoteText": r["clinical_note"],
        "revenueRisk": revenue,
        "readinessScore": readiness,
        "clinicalFacts": [
            {"id": str(f["id"]), "fact": f["fact"], "factAr": f["fact_ar"] or f["fact"], "category": f["category"],
             "source": f["source_label"], "date": _iso(f["fact_date"]) or "", "confidence": f["confidence"]}
            for f in rel.facts.get(cid, [])
        ],
        "policyRules": [
            {"id": str(q["id"]), "code": q["code"], "title": q["title"], "titleAr": q["title_ar"] or q["title"],
             "requirement": q["requirement"], "requirementAr": q["requirement_ar"] or q["requirement"],
             "status": q["status"], **({"evidenceSource": q["evidence_source"]} if q["evidence_source"] else {})}
            for q in rel.reqs.get(cid, [])
        ],
        "evidenceItems": [
            {"id": str(e["id"]), "requirement": e["requirement"], "requirementAr": e["requirement_ar"] or e["requirement"],
             "status": e["status"], "matchedFact": e["matched_fact"], "sourceEncounter": e["source_label"],
             "date": _iso(e["evidence_date"]), "confidence": e["confidence"]}
            for e in rel.evidence.get(cid, [])
        ],
        "agentRuns": [
            {"agentId": a["agent_id"], "name": a["name"], "nameAr": a["name_ar"] or a["name"], "status": a["status"],
             "outputSummary": a["output_summary"] or "", "outputSummaryAr": a["output_summary_ar"] or "",
             "durationMs": a["latency_ms"] or 0,
             "timestamp": a["started_at"].strftime("%Y-%m-%d %H:%M:%S")}
            for a in rel.runs.get(cid, [])
        ],
        "fhirPayload": rel.fhir.get(cid) or PENDING_FHIR,
        "auditTrail": [
            {"timestamp": e["occurred_at"].replace("T", " ")[:19],
             "action": e["details"].get("message", e["action"]),
             "actionAr": e["details"].get("message_ar", e["details"].get("message", e["action"])),
             "actor": e["details"].get("actor_label", e["actor_id"])}
            for e in rel.audit.get(cid, [])
        ],
    }
    if cid in rel.appeals:
        twin["appealPackage"] = rel.appeals[cid]
    discoverable = (r["extra"] or {}).get("discoverable_evidence")
    if discoverable:
        twin["discoverableEvidence"] = discoverable
    return twin


def _appeal_packages(conn: Connection, ids: list[str]) -> dict[str, dict[str, Any]]:
    rows = conn.execute(text(
        """
        SELECT DISTINCT ON (a.authorization_request_id) a.authorization_request_id AS case_id, a.id, a.strategy,
               a.strategy_ar, a.letter_en, a.letter_ar, a.strength, d.reason, d.reason_ar, d.root_cause,
               d.root_cause_ar, d.missing_requirement, d.missing_requirement_ar
        FROM appeals a LEFT JOIN denials d ON d.id = a.denial_id
        WHERE a.authorization_request_id = ANY(CAST(:ids AS uuid[]))
        ORDER BY a.authorization_request_id, a.created_at DESC
        """), {"ids": ids}).mappings().all()
    if not rows:
        return {}
    evidence: dict[str, list[Any]] = defaultdict(list)
    for e in conn.execute(text(
            "SELECT appeal_id, fact, fact_ar, source_label, evidence_date FROM appeal_evidence "
            "WHERE appeal_id = ANY(:a) ORDER BY appeal_id, ord"), {"a": [r["id"] for r in rows]}).mappings():
        evidence[str(e["appeal_id"])].append(e)
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        out[str(row["case_id"])] = {
            "denialReason": row["reason"] or "",
            "denialReasonAr": row["reason_ar"] or row["reason"] or "",
            "rootCause": row["root_cause"] or "",
            "rootCauseAr": row["root_cause_ar"] or row["root_cause"] or "",
            "missingRequirement": row["missing_requirement"] or "",
            "missingRequirementAr": row["missing_requirement_ar"] or row["missing_requirement"] or "",
            "foundEvidence": [
                {"fact": e["fact"], "factAr": e["fact_ar"] or e["fact"], "source": e["source_label"],
                 "date": _iso(e["evidence_date"]) or ""}
                for e in evidence.get(str(row["id"]), [])
            ],
            "appealStrength": row["strength"] or 0,
            "appealStrategy": row["strategy"] or "",
            "appealStrategyAr": row["strategy_ar"] or row["strategy"] or "",
            "formalLetterEn": row["letter_en"] or "",
            "formalLetterAr": row["letter_ar"] or "",
        }
    return out


def compute_metrics(conn: Connection) -> dict[str, Any]:
    """Command Center figures computed from stored data (no hard-coded numbers)."""
    row = conn.execute(text(
        """
        WITH latest AS (
          SELECT ar.id, ar.status, ar.financial_value_sar,
                 (SELECT overall_score FROM readiness_scores s WHERE s.authorization_request_id = ar.id
                  ORDER BY computed_at DESC LIMIT 1) AS score,
                 (SELECT revenue_at_risk_sar FROM revenue_risk r WHERE r.authorization_request_id = ar.id
                  ORDER BY computed_at DESC LIMIT 1) AS at_risk,
                 EXISTS (SELECT 1 FROM authorization_events e WHERE e.authorization_request_id = ar.id
                         AND e.to_status = 'RISK_DETECTED') AS had_risk
          FROM authorization_requests ar
        )
        SELECT
          coalesce(sum(financial_value_sar) FILTER (WHERE status = 'APPROVED'), 0) AS protected,
          coalesce(sum(at_risk) FILTER (WHERE status NOT IN ('APPROVED','RECOVERED')), 0) AS at_risk,
          coalesce(sum(financial_value_sar) FILTER (WHERE status = 'RECOVERED'), 0) AS recovered,
          count(*) FILTER (WHERE had_risk AND status IN ('DECISION_READY','SUBMITTED','APPROVED')) AS prevented,
          count(*) FILTER (WHERE status NOT IN ('APPROVED','RECOVERED')) AS active,
          count(*) FILTER (WHERE status IN ('DENIED','RECOVERY_IN_PROGRESS','APPEAL_READY')) AS recovery_queue,
          count(*) FILTER (WHERE status = 'APPROVED') AS approved,
          count(*) FILTER (WHERE status = 'APPROVED' AND NOT had_risk) AS clean_approved,
          avg(score) AS avg_score,
          count(*) AS total,
          count(score) AS analyzed
        FROM latest
        """)).mappings().one()
    approved = row["approved"] or 0
    return {
        "revenueProtectedTodaySAR": _num(row["protected"]),
        "revenueAtRiskSAR": _num(row["at_risk"]),
        "revenueRecoveredSAR": _num(row["recovered"]),
        "preventedDenialsCount": row["prevented"],
        "activeAuthorizationsCount": row["active"],
        "recoveryQueueCount": row["recovery_queue"],
        "cleanPassRate": round(100 * row["clean_approved"] / approved, 1) if approved else 0,
        "averageReadinessScore": round(float(row["avg_score"]), 1) if row["avg_score"] is not None else 0,
        "totalCases": row["total"],
        "analyzedCases": row["analyzed"],
        "basis": "Computed from stored cases. Demo and synthetic data only.",
    }
