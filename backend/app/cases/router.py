"""Case, metrics and audit endpoints."""

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import Connection, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import bindparam

from app.audit import service as audit
from app.cases import repository as repo
from app.cases.state_machine import CaseStatus, IllegalTransition, get_transition
from app.security.deps import CurrentUser, current_user, require, tenant_conn
from app.security.rbac import Permission, permissions_for

router = APIRouter(prefix="/api", tags=["cases"])


def _uuid(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found") from exc


@router.get("/cases")
def list_cases(
    status_filter: CaseStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: CurrentUser = Depends(require(Permission.CASE_READ)),
    conn: Connection = Depends(tenant_conn),
) -> dict[str, Any]:
    items = repo.list_cases(conn, status=status_filter.value if status_filter else None, q=q,
                            limit=limit, offset=offset)
    return {"items": items, "total": repo.count_cases(conn), "limit": limit, "offset": offset}


@router.get("/twins")
def list_twins(
    limit: int = Query(default=200, ge=1, le=500),
    _: CurrentUser = Depends(require(Permission.CASE_READ)),
    conn: Connection = Depends(tenant_conn),
) -> dict[str, Any]:
    """Full case views for the Command Center (bounded; fine for MVP volumes)."""
    ids = [c["id"] for c in repo.list_cases(conn, limit=limit)]
    return {"items": repo.build_twins(conn, ids)}


@router.get("/cases/{case_id}")
def get_case(
    case_id: str,
    _: CurrentUser = Depends(require(Permission.CASE_READ)),
    conn: Connection = Depends(tenant_conn),
) -> dict[str, Any]:
    twin = repo.build_twin(conn, _uuid(case_id))
    if twin is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return twin


class TransitionIn(BaseModel):
    to: CaseStatus
    note: str | None = Field(default=None, max_length=1000)


@router.post("/cases/{case_id}/transitions")
def transition(
    case_id: str,
    body: TransitionIn,
    user: CurrentUser = Depends(current_user),
    conn: Connection = Depends(tenant_conn),
) -> dict[str, Any]:
    cid = _uuid(case_id)
    row = conn.execute(text("SELECT status FROM authorization_requests WHERE id = :id FOR UPDATE"),
                       {"id": cid}).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    try:
        t = get_transition(row.status, body.to.value)
    except IllegalTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    if t.permission not in permissions_for(user.roles):
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Missing permission: {t.permission.value}")

    conn.execute(text("UPDATE authorization_requests SET status = :s, updated_at = now() WHERE id = :id"),
                 {"s": body.to.value, "id": cid})
    conn.execute(text(
        "INSERT INTO authorization_events (organization_id, authorization_request_id, from_status, to_status, "
        "actor, note) VALUES (:org, :id, :f, :t, :a, :n)"),
        {"org": user.org_id, "id": cid, "f": row.status, "t": body.to.value, "a": user.actor.id, "n": body.note})
    if t.human_gate:
        conn.execute(text(
            "INSERT INTO human_reviews (organization_id, authorization_request_id, reviewer_user_id, gate, "
            "decision, note) VALUES (:org, :id, :u, :g, 'APPROVED', :n)"),
            {"org": user.org_id, "id": cid, "u": user.id, "g": t.human_gate, "n": body.note})
    entry = audit.append(
        conn, org_id=user.org_id, chain_key=cid, actor=user.actor, action="case.transition",
        details={
            "from": row.status, "to": body.to.value, "human_gate": t.human_gate, "note": body.note,
            "message": f"Status changed {row.status} → {body.to.value}" + (" (human approval)" if t.human_gate else ""),
            "message_ar": f"تغيّرت الحالة من {row.status} إلى {body.to.value}"
                          + (" (موافقة بشرية)" if t.human_gate else ""),
            "actor_label": user.name or user.username,
        },
    )
    return {"id": cid, "from": row.status, "to": body.to.value, "audit_seq": entry["seq"]}


_insert_run = text(
    "INSERT INTO agent_runs (organization_id, authorization_request_id, agent_id, name, name_ar, status, "
    "output_summary, output_summary_ar, model, prompt_version, output, latency_ms) "
    "VALUES (:org, :id, 'A2', 'Evidence Hunter Agent', 'وكيل صيد الأدلة السريرية', 'COMPLETED', :s, :sar, "
    "'demo-data', 'n/a', :out, 0)"
).bindparams(bindparam("out", type_=JSONB))


@router.post("/cases/{case_id}/evidence-hunter/demo")
def evidence_hunter_demo(
    case_id: str,
    user: CurrentUser = Depends(require(Permission.CASE_ANALYZE)),
    conn: Connection = Depends(tenant_conn),
) -> dict[str, Any]:
    """Prototype behaviour preserved for the walkthrough: applies only evidence that the demo
    case record actually contains (``extra.discoverable_evidence``). The real retrieval agent is M2."""
    cid = _uuid(case_id)
    row = conn.execute(text(
        "SELECT status, financial_value_sar, extra FROM authorization_requests WHERE id = :id FOR UPDATE"),
        {"id": cid}).mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    found = (row["extra"] or {}).get("discoverable_evidence")
    if not found or not found.get("evidenceItems"):
        audit.append(conn, org_id=user.org_id, chain_key=cid, actor=user.actor, action="evidence_hunter.miss",
                     details={"message": "Evidence Hunter: no additional evidence found in the record. Case unchanged.",
                              "message_ar": "وكيل صيد الأدلة: لم يُعثر على أدلة إضافية في السجل. لم تتغير الحالة.",
                              "actor_label": "Mujeaz Evidence Hunter Agent"})
        return {"id": cid, "found": False}

    current = conn.execute(text(
        "SELECT * FROM readiness_scores WHERE authorization_request_id = :id ORDER BY computed_at DESC LIMIT 1"),
        {"id": cid}).mappings().first()
    after = found.get("readinessAfter", {})
    base = dict(current) if current else {}

    def pick(key: str, col: str) -> int:
        return int(after.get(key, base.get(col, 0)))

    overall = pick("overallScore", "overall_score")
    conn.execute(text(
        """INSERT INTO readiness_scores (organization_id, authorization_request_id, clinical_evidence, policy_match,
           documentation, coding_integrity, required_attachments, administrative_completeness, overall_score, label,
           label_ar, method)
           VALUES (:org, :id, :ce, :pm, :doc, :ci, :ra, :adm, :o, :l, :lar, 'demo-data')"""),
        {"org": user.org_id, "id": cid, "ce": pick("clinicalEvidence", "clinical_evidence"),
         "pm": pick("policyMatch", "policy_match"), "doc": pick("documentation", "documentation"),
         "ci": pick("codingIntegrity", "coding_integrity"), "ra": pick("requiredAttachments", "required_attachments"),
         "adm": pick("administrativeCompleteness", "administrative_completeness"), "o": overall,
         "l": after.get("readinessLabel", "Decision Ready"), "lar": after.get("readinessLabelAr", "جاهز للقرار")})
    prev_at_risk = conn.execute(text(
        "SELECT revenue_at_risk_sar FROM revenue_risk WHERE authorization_request_id = :id "
        "ORDER BY computed_at DESC LIMIT 1"), {"id": cid}).scalar() or 0
    p_after = int(found["denialRiskAfter"])
    value = float(row["financial_value_sar"])
    at_risk = round(value * p_after / 100)
    conn.execute(text(
        """INSERT INTO revenue_risk (organization_id, authorization_request_id, financial_value_sar, denial_risk_pct,
           revenue_at_risk_sar, recoverable_value_sar, priority)
           VALUES (:org, :id, :v, :p, :ar, :rec, :pr)"""),
        {"org": user.org_id, "id": cid, "v": value, "p": p_after, "ar": at_risk, "rec": at_risk,
         "pr": "HIGH" if p_after >= 60 else "MEDIUM" if p_after >= 30 else "LOW"})
    conn.execute(text("DELETE FROM authorization_evidence WHERE authorization_request_id = :id"), {"id": cid})
    for i, e in enumerate(found["evidenceItems"]):
        conn.execute(text(
            """INSERT INTO authorization_evidence (organization_id, authorization_request_id, requirement,
               requirement_ar, status, matched_fact, source_label, evidence_date, confidence, ord)
               VALUES (:org, :id, :r, :rar, :s, :m, :src, :d, :c, :o)"""),
            {"org": user.org_id, "id": cid, "r": e["requirement"], "rar": e.get("requirementAr"), "s": e["status"],
             "m": e.get("matchedFact"), "src": e.get("sourceEncounter"),
             "d": date.fromisoformat(e["date"]) if e.get("date") else None, "c": e.get("confidence", 0), "o": i})
    satisfied = found.get("satisfiesRuleIds", [])
    if satisfied:
        conn.execute(text(
            "UPDATE authorization_requirements SET status = 'PASSED', evidence_source = :src "
            "WHERE authorization_request_id = :id AND code = ANY(:codes)"),
            {"src": found.get("evidenceSource"), "id": cid, "codes": satisfied})
    conn.execute(_insert_run, {"org": user.org_id, "id": cid, "s": found["summary"], "sar": found["summaryAr"],
                               "out": {"evidence": found["evidenceItems"]}})
    prev_status = row["status"]
    new_status = "DECISION_READY" if overall >= 90 and prev_status in ("RISK_DETECTED", "EVIDENCE_SEARCHING") \
        else prev_status
    if new_status != prev_status:
        conn.execute(text("UPDATE authorization_requests SET status = :s, updated_at = now() WHERE id = :id"),
                     {"s": new_status, "id": cid})
        conn.execute(text(
            "INSERT INTO authorization_events (organization_id, authorization_request_id, from_status, to_status, "
            "actor) VALUES (:org, :id, :f, :t, 'agent:A2')"),
            {"org": user.org_id, "id": cid, "f": prev_status, "t": new_status})
    extra = dict(row["extra"] or {})
    extra.pop("discoverable_evidence", None)
    conn.execute(text("UPDATE authorization_requests SET extra = :e WHERE id = :id").bindparams(
        bindparam("e", type_=JSONB)), {"e": extra, "id": cid})
    prev_score = base.get("overall_score")
    audit.append(conn, org_id=user.org_id, chain_key=cid, actor=user.actor, action="evidence_hunter.found",
                 details={"message": f"Evidence Hunter: {found['summary']} Readiness {prev_score} → {overall}/100.",
                          "message_ar": f"وكيل صيد الأدلة: {found['summaryAr']} الجاهزية {prev_score} ← {overall}/100.",
                          "actor_label": "Mujeaz Evidence Hunter Agent", "status": new_status,
                          "denial_risk_pct": p_after})
    return {"id": cid, "found": True, "status": new_status, "overallScore": overall,
            "revenueProtected": max(0, round(float(prev_at_risk)) - at_risk)}


@router.get("/metrics")
def metrics(
    _: CurrentUser = Depends(require(Permission.METRICS_READ)),
    conn: Connection = Depends(tenant_conn),
) -> dict[str, Any]:
    return repo.compute_metrics(conn)


@router.get("/audit/{case_id}")
def audit_entries(
    case_id: str,
    _: CurrentUser = Depends(require(Permission.AUDIT_READ)),
    conn: Connection = Depends(tenant_conn),
) -> dict[str, Any]:
    cid = _uuid(case_id)
    if conn.execute(text("SELECT 1 FROM authorization_requests WHERE id = :id"), {"id": cid}).first() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return {"chain_key": cid, "entries": audit.list_chain(conn, cid)}


@router.get("/audit/{case_id}/verify")
def audit_verify(
    case_id: str,
    _: CurrentUser = Depends(require(Permission.AUDIT_READ)),
    conn: Connection = Depends(tenant_conn),
) -> dict[str, Any]:
    cid = _uuid(case_id)
    if conn.execute(text("SELECT 1 FROM authorization_requests WHERE id = :id"), {"id": cid}).first() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return audit.verify(conn, cid)
