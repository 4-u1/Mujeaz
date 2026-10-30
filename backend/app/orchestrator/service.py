"""Runs the analysis pipeline for a stored case and persists every result in one transaction.

A new analysis replaces the case's current facts, requirements and evidence; the full result of
every run is kept in `analysis_runs.result`, and each run is recorded in the audit chain.
"""

import hashlib
import re
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Connection, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import bindparam

from app.agents.types import Document, Mode, PatientRecord
from app.audit import service as audit
from app.audit.service import Actor
from app.cases.state_machine import CaseStatus, get_transition
from app.config import get_settings
from app.llm.provider import GeminiProvider, Provider
from app.nlp.chunker import chunk
from app.orchestrator.core import AnalysisResult, Emit, NoPolicy, analyze

ANALYZABLE = frozenset({CaseStatus.DRAFT, CaseStatus.RISK_DETECTED, CaseStatus.EVIDENCE_SEARCHING,
                        CaseStatus.DECISION_READY})
_ARABIC = re.compile(r"[؀-ۿ]")
CATEGORY = {"symptom_duration": "SYMPTOM", "persistent_symptoms": "SYMPTOM", "exam_slr": "EXAM",
            "red_flag": "EXAM", "conservative_therapy": "THERAPY", "claimed_therapy": "THERAPY",
            "therapy_not_attended": "THERAPY", "therapy_negated": "THERAPY", "medication": "MEDICATION",
            "requested_service": "ORDER"}


class CaseNotFound(Exception):
    pass


class NotAnalyzable(Exception):
    pass


def _j(sql: str, *cols: str) -> Any:
    return text(sql).bindparams(*(bindparam(c, type_=JSONB) for c in cols))


def default_provider() -> Provider | None:
    s = get_settings()
    return GeminiProvider(s.gemini_api_key, s.gemini_model) if s.gemini_api_key else None


def _language(t: str) -> str:
    ar = bool(_ARABIC.search(t))
    return "mixed" if ar and re.search(r"[A-Za-z]{3,}", t) else "ar" if ar else "en"


def load_record(conn: Connection, case_id: str, org_id: str, *, lock: bool = True
                ) -> tuple[Any, PatientRecord, dict[str, str]]:
    row = conn.execute(text(
        "SELECT ar.id, ar.case_number, ar.status, ar.patient_id, ar.service_code, ar.diagnosis_code, "
        "ar.financial_value_sar, ar.clinical_note, ar.requested_on, p.code AS payer_code "
        "FROM authorization_requests ar JOIN payers p ON p.id = ar.payer_id WHERE ar.id = :id"
        + (" FOR UPDATE OF ar" if lock else "")),
        {"id": case_id}).mappings().first()
    if row is None:
        raise CaseNotFound(case_id)
    if CaseStatus(row["status"]) not in ANALYZABLE:
        raise NotAnalyzable(f"Cases in status {row['status']} cannot be re-analysed")
    docs = conn.execute(text(
        "SELECT id, doc_ref, doc_type, language, authored_on, content FROM clinical_documents "
        "WHERE patient_id = :p AND ((authorization_request_id IS NULL AND authored_on <= :d) "
        "OR authorization_request_id = :c) "
        "ORDER BY (doc_type = 'addendum'), authored_on DESC, doc_ref"),
        {"p": row["patient_id"], "d": row["requested_on"], "c": case_id}).mappings().all()
    if not docs:
        # Legacy cases carry only the clinical note: store it as the case's index document so
        # every fact can still point at a verified span in a stored document.
        note = row["clinical_note"]
        conn.execute(text(
            "INSERT INTO clinical_documents (organization_id, patient_id, doc_ref, doc_type, language, authored_on, "
            "content, content_sha256) VALUES (:o, :p, :r, 'clinical-note', :l, :d, :c, :h) "
            "ON CONFLICT (organization_id, doc_ref) DO NOTHING"),
            {"o": org_id, "p": row["patient_id"], "r": f"{row['case_number']}-NOTE", "l": _language(note),
             "d": row["requested_on"], "c": note, "h": hashlib.sha256(note.encode()).hexdigest()})
        return load_record(conn, case_id, org_id, lock=lock)
    documents = tuple(Document(d["doc_ref"], d["doc_type"], d["language"], d["authored_on"], d["content"])
                      for d in docs)
    index = next((d.doc_ref for d in documents if d.text == row["clinical_note"]), documents[0].doc_ref)
    record = PatientRecord(row["case_number"], documents, row["diagnosis_code"], row["service_code"],
                           row["payer_code"], row["requested_on"], index)
    return row, record, {d["doc_ref"]: str(d["id"]) for d in docs}


def index_chunks(conn: Connection, org_id: str, doc_ids: dict[str, str], record: PatientRecord) -> int:
    """Sentence chunks with exact offsets for full-text search (ADR 0006). Idempotent per document."""
    n = 0
    for d in record.documents:
        for c in chunk(d.text):
            n += conn.execute(text(
                "INSERT INTO document_chunks (organization_id, document_id, ord, char_start, char_end, content) "
                "VALUES (:o, :d, :i, :s, :e, :c) ON CONFLICT (document_id, ord) DO NOTHING"),
                {"o": org_id, "d": doc_ids[d.doc_ref], "i": c.ord, "s": c.start, "e": c.end, "c": c.text}).rowcount
    return n


def _result_json(res: AnalysisResult) -> dict[str, Any]:
    return {
        "mode": res.mode, "policy_version": res.policy_version, "fallback_reason": res.fallback_reason,
        "facts": [{**asdict(f), "fact_date": f.fact_date.isoformat() if f.fact_date else None} for f in res.facts],
        "rejected_quotes": res.rejected_quotes,
        "injection_flags": [asdict(f) for f in res.injection_flags],
        "evidence": {k: {"status": v.status, "reason": v.reason, "cdi_question": v.cdi_question,
                         "retrieved": [list(x) for x in v.retrieved]} for k, v in res.evidence.items()},
        "rules": [asdict(r) for r in res.rules],
        "readiness": {"components": res.readiness.components, "overall": res.readiness.overall,
                      "gate": res.readiness.gate, "denial_risk": res.readiness.denial_risk,
                      "explanation": res.readiness.explanation,
                      "decision_ready_min": res.decision_ready_min},
        "excluded_addenda": list(res.excluded_addenda),
    }


def run_analysis(conn: Connection, *, case_id: str, org_id: str, actor: Actor, actor_label: str,
                 mode: Mode | None = None, provider: Provider | None = None, emit: Emit | None = None) -> dict[str, Any]:
    row, record, doc_ids = load_record(conn, case_id, org_id)
    current = CaseStatus(row["status"])
    provider = provider if provider is not None else default_provider()
    requested: Mode = mode or ("llm" if provider is not None else "baseline")
    fallback_note = "LLM requested but no model is configured; baseline used" \
        if requested == "llm" and provider is None else None

    run_id = conn.execute(text(
        "INSERT INTO analysis_runs (organization_id, authorization_request_id, mode, requested_mode, status, actor_id) "
        "VALUES (:o, :c, :m, :m, 'RUNNING', :a) RETURNING id"),
        {"o": org_id, "c": case_id, "m": requested, "a": actor.id}).scalar_one()
    index_chunks(conn, org_id, doc_ids, record)
    res = analyze(record, mode=requested, provider=provider, price_sar=float(row["financial_value_sar"]),
                  emit=emit or (lambda _k, _d: None))
    fallback = res.fallback_reason or fallback_note

    old_spans = [r[0] for r in conn.execute(text(
        "SELECT evidence_span_id FROM clinical_facts WHERE authorization_request_id = :c "
        "AND evidence_span_id IS NOT NULL"), {"c": case_id})]
    for table in ("clinical_facts", "authorization_evidence", "authorization_requirements"):
        conn.execute(text(f"DELETE FROM {table} WHERE authorization_request_id = :c"), {"c": case_id})  # noqa: S608
    if old_spans:  # spans belonged only to the replaced facts; the full previous result stays in analysis_runs
        conn.execute(text("DELETE FROM evidence_spans WHERE id = ANY(CAST(:ids AS uuid[]))"),
                     {"ids": [str(x) for x in old_spans]})

    span_of: dict[int, str] = {}
    for i, f in enumerate(res.facts):
        span = conn.execute(text(
            "INSERT INTO evidence_spans (organization_id, document_id, char_start, char_end, quoted) "
            "VALUES (:o, :d, :s, :e, :q) RETURNING id"),
            {"o": org_id, "d": doc_ids[f.doc_ref], "s": f.start, "e": f.end, "q": f.quote}).scalar_one()
        span_of[id(f)] = str(span)
        doc = next(d for d in record.documents if d.doc_ref == f.doc_ref)
        conn.execute(_j(
            "INSERT INTO clinical_facts (organization_id, authorization_request_id, document_id, category, fact, "
            "source_label, char_start, char_end, fact_date, confidence, ord, analysis_run_id, label, value, quote, "
            "evidence_span_id) VALUES (:o, :c, :d, :cat, :fact, :src, :s, :e, :fd, :conf, :i, :run, :lab, :val, "
            ":q, :span)", "val"),
            {"o": org_id, "c": case_id, "d": doc_ids[f.doc_ref], "cat": CATEGORY.get(f.label, "OTHER"),
             "fact": f.quote, "src": f"{doc.doc_type} · {f.doc_ref}", "s": f.start, "e": f.end, "fd": f.fact_date,
             "conf": f.confidence, "i": i, "run": run_id, "lab": f.label, "val": f.value, "q": f.quote,
             "span": span})

    rule_ids = {r.code: r.id for r in conn.execute(text(
        "SELECT pr.id, pr.code FROM policy_rules pr JOIN policy_versions pv ON pv.id = pr.policy_version_id "
        "JOIN payer_policies pp ON pp.id = pv.policy_id WHERE pp.code = :p AND pv.version = :v"),
        dict(zip(("p", "v"), res.policy_version.split("@", 1), strict=True)))}
    from app.rules import engine  # local import keeps the policy cache out of module import time

    policy = engine.policy_for(record.payer_code, record.service_code)
    assert policy is not None
    rule_meta = {r["code"]: r for r in policy.rules}
    for i, r in enumerate(res.rules):
        m = rule_meta[r.code]
        ev = res.evidence.get(r.rule_id)
        src = ev.facts[0] if ev and ev.facts else None
        conn.execute(text(
            "INSERT INTO authorization_requirements (organization_id, authorization_request_id, policy_rule_id, code, "
            "title, title_ar, requirement, requirement_ar, status, evidence_source, ord, analysis_run_id, reason, "
            "reason_ar) VALUES (:o, :c, :rule, :code, :t, :ta, :r, :ra, :s, :src, :i, :run, :why, :why_ar)"),
            {"o": org_id, "c": case_id, "rule": rule_ids.get(r.code), "code": r.code, "t": m["title"],
             "ta": m.get("title_ar"), "r": " ".join(m["requirement"].split()),
             "ra": " ".join(m.get("requirement_ar", "").split()) or None, "s": r.outcome,
             "src": f"{src.doc_ref}" if src else None, "i": i, "run": run_id, "why": r.reason, "why_ar": r.reason_ar})
    for i, (rid, ev) in enumerate(res.evidence.items()):
        spec = policy.requirements[rid]
        best = ev.facts[0] if ev.facts else None
        conn.execute(text(
            "INSERT INTO authorization_evidence (organization_id, authorization_request_id, requirement, requirement_ar, "
            "status, matched_fact, source_label, evidence_date, confidence, evidence_span_id, ord, analysis_run_id, "
            "requirement_id, cdi_question, cdi_question_ar) VALUES (:o, :c, :r, :ra, :s, :mf, :src, :d, :conf, "
            ":span, :i, :run, :rid, :q, :qa)"),
            {"o": org_id, "c": case_id, "r": spec["title"], "ra": spec.get("title_ar"), "s": ev.status,
             "mf": ev.reason if best is None else f"{best.quote} — {ev.reason}",
             "src": f"{best.doc_ref}" if best else None, "d": best.fact_date if best else None,
             "conf": best.confidence if best else 0, "span": span_of.get(id(best)) if best else None, "i": i,
             "run": run_id, "rid": rid, "q": " ".join(ev.cdi_question.split()) if ev.cdi_question else None,
             "qa": " ".join(ev.cdi_question_ar.split()) if ev.cdi_question_ar else None})

    rd = res.readiness
    c = rd.components
    conn.execute(text(
        "INSERT INTO readiness_scores (organization_id, authorization_request_id, clinical_evidence, policy_match, "
        "documentation, coding_integrity, required_attachments, administrative_completeness, overall_score, label, "
        "label_ar, gate_applied, warning, warning_ar, method) VALUES (:o, :c, :ce, :pm, :doc, :ci, :ra, :ac, :ov, "
        ":l, :la, :g, :w, :wa, :m)"),
        {"o": org_id, "c": case_id, "ce": c["clinicalEvidence"], "pm": c["policyMatch"], "doc": c["documentation"],
         "ci": c["codingIntegrity"], "ra": c["requiredAttachments"], "ac": c["administrativeCompleteness"],
         "ov": rd.overall, "l": rd.label, "la": rd.label_ar, "g": rd.gate, "w": rd.warning, "wa": rd.warning_ar,
         "m": f"agents-{res.mode}-v1"})
    rv = rd.revenue
    conn.execute(text(
        "INSERT INTO revenue_risk (organization_id, authorization_request_id, financial_value_sar, denial_risk_pct, "
        "revenue_at_risk_sar, recoverable_value_sar, priority) VALUES (:o, :c, :v, :p, :r, :rec, :pr)"),
        {"o": org_id, "c": case_id, "v": rv.financial_value, "p": rd.denial_risk, "r": rv.revenue_at_risk,
         "rec": rv.recoverable_value, "pr": rv.priority})
    for s in res.steps:
        conn.execute(_j(
            "INSERT INTO agent_runs (organization_id, authorization_request_id, agent_id, name, name_ar, status, "
            "output_summary, output_summary_ar, model, prompt_version, output, latency_ms, analysis_run_id) "
            "VALUES (:o, :c, :a, :n, :na, :s, :os, :osa, :m, :pv, :out, :ms, :run)", "out"),
            {"o": org_id, "c": case_id, "a": s.agent_id, "n": s.name, "na": s.name_ar, "s": s.status,
             "os": s.summary, "osa": s.summary_ar, "m": s.model, "pv": s.prompt_version, "out": s.output,
             "ms": s.latency_ms, "run": run_id})

    target = CaseStatus.DECISION_READY if res.decision_ready else CaseStatus.RISK_DETECTED
    if target != current:
        get_transition(current.value, target.value)  # raises if the lifecycle table forbids it
        conn.execute(text("UPDATE authorization_requests SET status = :s, updated_at = now() WHERE id = :id"),
                     {"s": target.value, "id": case_id})
        conn.execute(text(
            "INSERT INTO authorization_events (organization_id, authorization_request_id, from_status, to_status, "
            "actor, note) VALUES (:o, :c, :f, :t, :a, :n)"),
            {"o": org_id, "c": case_id, "f": current.value, "t": target.value, "a": actor.id,
             "n": f"analysis {run_id}"})

    from app.cdi.service import sync_queries  # local import: cdi.service imports this module

    queries = sync_queries(conn, org_id=org_id, case_id=case_id, run_id=str(run_id), res=res, actor=actor,
                           actor_label=actor_label)
    summary = {k: v.status for k, v in res.evidence.items()} | {r.code: r.outcome for r in res.rules}
    conn.execute(_j(
        "UPDATE analysis_runs SET status = 'COMPLETED', mode = :m, policy_version = :pv, fallback_reason = :fb, "
        "result = :res, finished_at = clock_timestamp() WHERE id = :id", "res"),
        {"m": res.mode, "pv": res.policy_version, "fb": fallback, "res": _result_json(res), "id": run_id})
    if res.injection_flags:
        audit.append(conn, org_id=org_id, chain_key=case_id, actor=actor, action="analysis.injection_flagged",
                     details={"analysis_run_id": str(run_id), "count": len(res.injection_flags),
                              "documents": sorted({f.doc_ref for f in res.injection_flags}),
                              "message": f"{len(res.injection_flags)} instruction-like passage(s) flagged in clinical "
                                         "text; ignored by the pipeline",
                              "message_ar": f"رُصد {len(res.injection_flags)} مقطع يشبه التعليمات في النص السريري وتم تجاهله",
                              "actor_label": actor_label})
    audit.append(conn, org_id=org_id, chain_key=case_id, actor=actor, action="case.analyzed",
                 details={"analysis_run_id": str(run_id), "mode": res.mode, "requested_mode": requested,
                          "policy_version": res.policy_version, "fallback_reason": fallback, "outcomes": summary,
                          "facts": len(res.facts), "rejected_quotes": len(res.rejected_quotes),
                          "readiness": rd.overall, "from": current.value, "to": target.value,
                          "message": f"Analysis ({res.mode}): readiness {rd.overall}/100, {current.value} → {target.value}",
                          "message_ar": f"تحليل ({res.mode}): الجاهزية {rd.overall}/100، {current.value} ← {target.value}",
                          "actor_label": actor_label},
                 occurred_at=datetime.now(UTC))
    return {"analysis_run_id": str(run_id), "mode": res.mode, "requested_mode": requested, "fallback_reason": fallback,
            "policy_version": res.policy_version, "status": target.value, "readiness": rd.overall,
            "outcomes": summary, "facts": len(res.facts), "rejected_quotes": len(res.rejected_quotes),
            "injection_flags": len(res.injection_flags), "documentation_queries": queries}


__all__ = ["CaseNotFound", "NoPolicy", "NotAnalyzable", "run_analysis"]
