"""Physician documentation queries (CDI): open, withdraw, answer, decline — and the what-if simulator.

A query is opened for every requirement whose rule did not pass after an analysis, and withdrawn
when a later analysis satisfies it. Answering renders a structured addendum, stores it as a signed
case document and re-analyses the case in the same transaction (decision D5).
"""

import hashlib
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import Connection, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import bindparam

from app.agents.types import Document
from app.audit import service as audit
from app.audit.service import Actor
from app.cdi.addendum import RedFlagAnswer, TherapyAnswer, render, validate_against_request
from app.orchestrator.core import AnalysisResult, analyze
from app.orchestrator.service import load_record, run_analysis

SYSTEM_CDI = Actor(id="system:cdi", role="system")
QUERY_DUE_DAYS = 2


class QueryNotFound(Exception):
    pass


class QueryClosed(Exception):
    pass


class InvalidAnswer(Exception):
    pass


def _today() -> date:
    return datetime.now(UTC).date()


def sync_queries(conn: Connection, *, org_id: str, case_id: str, run_id: str, res: AnalysisResult, actor: Actor,
                 actor_label: str) -> dict[str, int]:
    """Opens a query per unmet requirement that has a documentation question; withdraws met ones."""
    opened = withdrawn = 0
    open_rows = {r.requirement_id: r.id for r in conn.execute(text(
        "SELECT id, requirement_id FROM documentation_queries WHERE authorization_request_id = :c AND status = 'OPEN'"),
        {"c": case_id})}
    unmet = {r.rule_id for r in res.rules if r.outcome != "PASSED"}
    for rid, ev in res.evidence.items():
        if rid in unmet and ev.cdi_question and rid not in open_rows:
            conn.execute(text(
                "INSERT INTO documentation_queries (organization_id, authorization_request_id, requirement_id, "
                "question, question_ar, status, created_by, due_on, analysis_run_id) "
                "VALUES (:o, :c, :r, :q, :qa, 'OPEN', :by, :due, :run)"),
                {"o": org_id, "c": case_id, "r": rid, "q": " ".join(ev.cdi_question.split()),
                 "qa": " ".join((ev.cdi_question_ar or "").split()) or None, "by": actor.id,
                 "due": _today() + timedelta(days=QUERY_DUE_DAYS), "run": run_id})
            opened += 1
            audit.append(conn, org_id=org_id, chain_key=case_id, actor=actor, action="cdi.query_opened",
                         details={"requirement_id": rid, "analysis_run_id": run_id,
                                  "message": f"Documentation query sent to the physician for {rid}",
                                  "message_ar": f"أُرسل سؤال توثيق للطبيب بخصوص {rid}", "actor_label": actor_label})
    for rid, qid in open_rows.items():
        if rid not in unmet:
            conn.execute(text(
                "UPDATE documentation_queries SET status = 'WITHDRAWN', closed_by = :by, closed_at = clock_timestamp() "
                "WHERE id = :id"), {"by": actor.id, "id": qid})
            withdrawn += 1
            audit.append(conn, org_id=org_id, chain_key=case_id, actor=actor, action="cdi.query_withdrawn",
                         details={"requirement_id": rid, "query_id": str(qid), "analysis_run_id": run_id,
                                  "message": f"Documentation query for {rid} withdrawn: requirement now met",
                                  "message_ar": f"سُحب سؤال التوثيق لـ {rid}: الشرط مستوفى الآن",
                                  "actor_label": actor_label})
    return {"opened": opened, "withdrawn": withdrawn}


def _outcome(res: AnalysisResult) -> dict[str, Any]:
    return {"readiness": res.readiness.overall, "denialRisk": res.readiness.denial_risk,
            "revenueAtRisk": res.readiness.revenue.revenue_at_risk,
            "status": "DECISION_READY" if res.decision_ready else "RISK_DETECTED",
            "evidence": {k: v.status for k, v in res.evidence.items()},
            "rules": {r.code: r.outcome for r in res.rules},
            "reasons": {k: v.reason for k, v in res.evidence.items()}}


def simulate(conn: Connection, *, case_id: str, org_id: str, answer: TherapyAnswer | RedFlagAnswer,
             language: Literal["en", "ar"], author: str) -> dict[str, Any]:
    """What-if: the current record versus the record plus the addendum this answer would create.

    Runs the pure pipeline only; the caller's transaction is rolled back, so nothing is stored.
    """
    row, record, _ = load_record(conn, case_id, org_id, lock=False)
    try:
        validate_against_request(answer, row["requested_on"], _today())
    except ValueError as exc:
        raise InvalidAnswer(str(exc)) from exc
    price = float(row["financial_value_sar"])
    before = analyze(record, price_sar=price)
    body = render(answer, case_number=row["case_number"], language=language, author=author)
    hypo = Document(f"{row['case_number']}-ADD-SIM", "addendum", language, _today(), body)
    after = analyze(replace(record, documents=(*record.documents, hypo)), price_sar=price)
    return {"simulation": True, "policyVersion": after.policy_version, "addendumPreview": body,
            "addendumAccepted": not after.excluded_addenda,
            "before": _outcome(before), "after": _outcome(after),
            "delta": {"readiness": after.readiness.overall - before.readiness.overall,
                      "revenueAtRisk": after.readiness.revenue.revenue_at_risk - before.readiness.revenue.revenue_at_risk}}


def _lock_open_query(conn: Connection, query_id: str) -> Any:
    q = conn.execute(text(
        "SELECT q.id, q.authorization_request_id, q.requirement_id, q.status, ar.case_number, ar.requested_on, "
        "ar.patient_id FROM documentation_queries q JOIN authorization_requests ar ON ar.id = q.authorization_request_id "
        "WHERE q.id = :id FOR UPDATE OF q"), {"id": query_id}).mappings().first()
    if q is None:
        raise QueryNotFound(query_id)
    if q["status"] != "OPEN":
        raise QueryClosed(f"Query is {q['status']}")
    return q


def answer_query(conn: Connection, *, query_id: str, org_id: str, user_id: str, actor: Actor, actor_label: str,
                 answer: TherapyAnswer | RedFlagAnswer, language: Literal["en", "ar"]) -> dict[str, Any]:
    q = _lock_open_query(conn, query_id)
    case_id = str(q["authorization_request_id"])
    try:
        validate_against_request(answer, q["requested_on"], _today())
    except ValueError as exc:
        raise InvalidAnswer(str(exc)) from exc
    body = render(answer, case_number=q["case_number"], language=language, author=actor_label)
    n = conn.execute(text("SELECT count(*) FROM clinical_documents WHERE authorization_request_id = :c"),
                     {"c": case_id}).scalar_one()
    doc_ref = f"{q['case_number']}-ADD{n + 1}"
    doc_id = conn.execute(text(
        "INSERT INTO clinical_documents (organization_id, patient_id, doc_ref, doc_type, language, authored_on, content, "
        "content_sha256, authorization_request_id, author_user_id, signed_at, query_id) VALUES (:o, :p, :r, 'addendum', "
        ":l, :d, :c, :h, :case, :u, clock_timestamp(), :q) RETURNING id"),
        {"o": org_id, "p": q["patient_id"], "r": doc_ref, "l": language, "d": _today(), "c": body,
         "h": hashlib.sha256(body.encode()).hexdigest(), "case": case_id, "u": user_id, "q": query_id}).scalar_one()
    conn.execute(text(
        "UPDATE documentation_queries SET status = 'ANSWERED', closed_by = :by, closed_at = clock_timestamp(), "
        "answer = :a, addendum_document_id = :d WHERE id = :id").bindparams(bindparam("a", type_=JSONB)),
        {"by": actor.id, "a": answer.model_dump(mode="json"), "d": doc_id, "id": query_id})
    audit.append(conn, org_id=org_id, chain_key=case_id, actor=actor, action="cdi.query_answered",
                 details={"query_id": query_id, "requirement_id": q["requirement_id"], "document": doc_ref,
                          "content_sha256": hashlib.sha256(body.encode()).hexdigest(),
                          "message": f"Physician answered the documentation query with addendum {doc_ref}",
                          "message_ar": f"أجاب الطبيب على سؤال التوثيق بالملحق {doc_ref}",
                          "actor_label": actor_label})
    result = run_analysis(conn, case_id=case_id, org_id=org_id, actor=SYSTEM_CDI,
                          actor_label=f"Automatic re-analysis after {doc_ref}")
    return {"query_id": query_id, "document": doc_ref, "addendum": body, "analysis": result}


def decline_query(conn: Connection, *, query_id: str, org_id: str, actor: Actor, actor_label: str,
                  reason: str) -> dict[str, Any]:
    q = _lock_open_query(conn, query_id)
    case_id = str(q["authorization_request_id"])
    conn.execute(text(
        "UPDATE documentation_queries SET status = 'DECLINED', closed_by = :by, closed_at = clock_timestamp(), "
        "decline_reason = :r WHERE id = :id"), {"by": actor.id, "r": reason, "id": query_id})
    audit.append(conn, org_id=org_id, chain_key=case_id, actor=actor, action="cdi.query_declined",
                 details={"query_id": query_id, "requirement_id": q["requirement_id"], "reason": reason,
                          "message": f"Physician declined the documentation query: {reason}",
                          "message_ar": f"اعتذر الطبيب عن سؤال التوثيق: {reason}", "actor_label": actor_label})
    return {"query_id": query_id, "status": "DECLINED"}


def list_queries(conn: Connection, *, status: str | None, case_id: str | None = None) -> list[dict[str, Any]]:
    rows = conn.execute(text(
        "SELECT q.id, q.authorization_request_id, ar.case_number, ar.requested_service, ar.requested_on, "
        "q.requirement_id, q.question, q.question_ar, q.status, q.created_at, q.due_on, q.closed_at, q.closed_by, "
        "q.decline_reason, d.doc_ref AS addendum_ref "
        "FROM documentation_queries q JOIN authorization_requests ar ON ar.id = q.authorization_request_id "
        "LEFT JOIN clinical_documents d ON d.id = q.addendum_document_id "
        "WHERE (CAST(:s AS text) IS NULL OR q.status = :s) AND (CAST(:c AS uuid) IS NULL OR q.authorization_request_id = :c) "
        "ORDER BY q.status = 'OPEN' DESC, q.due_on, q.created_at"), {"s": status, "c": case_id}).mappings()
    return [{"id": str(r["id"]), "caseId": str(r["authorization_request_id"]), "caseNumber": r["case_number"],
             "requestedService": r["requested_service"], "requestedOn": r["requested_on"].isoformat(),
             "requirementId": r["requirement_id"], "question": r["question"],
             "questionAr": r["question_ar"] or r["question"], "status": r["status"],
             "createdAt": r["created_at"].isoformat(), "dueOn": r["due_on"].isoformat() if r["due_on"] else None,
             "closedAt": r["closed_at"].isoformat() if r["closed_at"] else None, "closedBy": r["closed_by"],
             "declineReason": r["decline_reason"], "addendumRef": r["addendum_ref"]} for r in rows]
