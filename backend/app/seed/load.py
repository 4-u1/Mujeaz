"""Loads demo data: organisations, users, demo payers/policy, the three legacy demo cases,
and the 50 synthetic MRI Lumbar Spine bundles. Runs on the owner connection.

Idempotent: if the demo organisation exists, nothing is loaded unless ``reset=True``.
"""

import base64
import hashlib
import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import bindparam

from app.audit import service as audit
from app.audit.service import Actor
from app.llm.provider import PROMPT_DIR, load_prompt
from app.nlp.chunker import chunk
from app.rules import engine
from app.security.rbac import ROLE_DESCRIPTIONS
from app.seed.constants import (
    DEMO_ORG_ID,
    DEMO_ORG_NAME,
    DEMO_PAYERS,
    DEMO_USERS,
    MRI_LUMBAR_CODE,
    MRI_LUMBAR_PRICE_SAR,
    OTHER_ORG_ID,
    OTHER_ORG_NAME,
    OTHER_ORG_USER,
)

log = logging.getLogger("mujeaz.seed")
SEED_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SYNTHETIC_DIR = REPO_ROOT / "evals" / "data" / "mri_lumbar"
SEED_ACTOR = Actor(id="system:seed", role="system")

_POLICY = engine.policy_for("DPA", MRI_LUMBAR_CODE)
assert _POLICY is not None, "Demo Payer A lumbar MRI policy YAML is missing"
POLICY_TEXT: str = _POLICY.raw["source_text"]
POLICY_VERSION: str = _POLICY.version
RULES = [
    {"code": r["code"], "title": r["title"], "title_ar": r.get("title_ar"),
     "requirement": " ".join(r["requirement"].split()), "requirement_ar": " ".join(r.get("requirement_ar", "").split()),
     "spec": {k: v for k, v in r.items() if k not in ("code", "title", "title_ar", "requirement", "requirement_ar")}}
    for r in _POLICY.rules
]


def _j(sql: str, *names: str) -> Any:
    stmt = text(sql)
    return stmt.bindparams(*[bindparam(n, type_=JSONB) for n in names]) if names else stmt


def _exec(conn: Connection, sql: str, params: dict[str, Any], *json_cols: str) -> Any:
    return conn.execute(_j(sql, *json_cols), params)


def _bind(conn: Connection, org: str) -> None:
    conn.execute(text("SELECT set_config('app.org_id', :o, true)"), {"o": org})


def _split(bilingual: str) -> tuple[str, str | None]:
    if " / " in bilingual:
        ar, en = bilingual.split(" / ", 1)
        return en.strip(), ar.strip()
    return bilingual, None


def _ts(s: str) -> datetime:
    return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)


def seed(conn: Connection, synthetic_dir: Path | None = None, reset: bool = False) -> dict[str, int]:
    exists = conn.execute(text("SELECT 1 FROM organizations WHERE id = :id"), {"id": DEMO_ORG_ID}).first()
    if exists and not reset:
        log.info("demo data already present; skipping")
        return {"skipped": 1}
    if exists:
        conn.execute(text("ALTER TABLE audit_logs DISABLE TRIGGER audit_logs_no_update"))
        conn.execute(text("DELETE FROM audit_logs"))
        conn.execute(text("ALTER TABLE audit_logs ENABLE TRIGGER audit_logs_no_update"))
        conn.execute(text("DELETE FROM organizations"))

    for role, desc in ROLE_DESCRIPTIONS.items():
        conn.execute(text("INSERT INTO roles (name, description) VALUES (:n, :d) ON CONFLICT (name) DO NOTHING"),
                     {"n": role.value, "d": desc})
    counts = {"organizations": 0, "users": 0, "legacy_cases": 0, "synthetic_cases": 0, "prompts": 0}
    counts["prompts"] = register_prompts(conn)
    for org_id, name in ((DEMO_ORG_ID, DEMO_ORG_NAME), (OTHER_ORG_ID, OTHER_ORG_NAME)):
        conn.execute(text("INSERT INTO organizations (id, name) VALUES (:id, :n)"), {"id": org_id, "n": name})
        counts["organizations"] += 1

    for u in (*DEMO_USERS, OTHER_ORG_USER):
        uid = conn.execute(text(
            "INSERT INTO users (organization_id, username, display_name) VALUES (:o, :u, :n) RETURNING id"),
            {"o": u.org_id, "u": u.username, "n": u.display_name}).scalar_one()
        conn.execute(text("INSERT INTO user_roles (organization_id, user_id, role_name) VALUES (:o, :u, :r)"),
                     {"o": u.org_id, "u": uid, "r": u.role})
        counts["users"] += 1

    ctx = _reference_data(conn, DEMO_ORG_ID)
    for case in json.loads((SEED_DIR / "legacy_cases.json").read_text(encoding="utf-8")):
        _load_legacy_case(conn, ctx, case)
        counts["legacy_cases"] += 1

    folder = synthetic_dir or DEFAULT_SYNTHETIC_DIR
    if folder.exists():
        for path in sorted(folder.glob("SYN-*.json")):
            _load_bundle(conn, ctx, json.loads(path.read_text(encoding="utf-8")))
            counts["synthetic_cases"] += 1
    else:
        log.warning("synthetic dataset not found at %s", folder)

    # One case in the other organisation, used by the isolation tests.
    other = _reference_data(conn, OTHER_ORG_ID)
    pid = _patient(conn, OTHER_ORG_ID, "OTHER-P-1", "Other Org Patient (synthetic)", 1980, "F")
    _request(conn, other, OTHER_ORG_ID, case_number="OTHER-0001", legacy_id=None, patient_id=pid,
             facility_id=other["facility"], payer_id=other["payers"]["DPA"], physician="Dr. Other",
             specialty="Orthopedics", service="MRI Lumbar Spine", service_ar=None, service_code=MRI_LUMBAR_CODE,
             dx_code="M54.16", dx_display="Radiculopathy, lumbar region", value=MRI_LUMBAR_PRICE_SAR,
             status="DRAFT", note="Other organisation note (isolation test).", source="synthetic",
             requested_on=date(2026, 9, 1))
    return counts


def register_prompts(conn: Connection) -> int:
    """Registers every versioned prompt file (name, version, SHA-256, body). Idempotent."""
    n = 0
    for path in sorted(PROMPT_DIR.glob("*.md")):
        p = load_prompt(path.stem)
        n += conn.execute(text(
            "INSERT INTO prompts (name, version, body_sha256, body) VALUES (:n, :v, :h, :b) "
            "ON CONFLICT (name, version) DO NOTHING"),
            {"n": p.name, "v": p.version, "h": p.sha256, "b": f"{p.system}\n---\n{p.template}"}).rowcount
    return n


def _reference_data(conn: Connection, org: str) -> dict[str, Any]:
    _bind(conn, org)
    payers = {}
    for code, name, name_ar in DEMO_PAYERS:
        payers[code] = conn.execute(text(
            "INSERT INTO payers (organization_id, code, name, name_ar) VALUES (:o, :c, :n, :a) RETURNING id"),
            {"o": org, "c": code, "n": name, "a": name_ar}).scalar_one()
    facility = conn.execute(text(
        "INSERT INTO facilities (organization_id, code, name, name_ar) VALUES (:o, 'DEMO-HOSP-01', "
        "'Demo General Hospital, Riyadh', 'مستشفى تجريبي عام - الرياض') RETURNING id"), {"o": org}).scalar_one()
    policy = conn.execute(text(
        "INSERT INTO payer_policies (organization_id, payer_id, code, title, title_ar) VALUES "
        "(:o, :p, 'DPA-LUMBAR-POL', 'Lumbar Spine MRI Prior Authorization (demo)', "
        "'سياسة الموافقة المسبقة للرنين المغناطيسي القطني (تجريبية)') RETURNING id"),
        {"o": org, "p": payers["DPA"]}).scalar_one()
    version = conn.execute(text(
        "INSERT INTO policy_versions (organization_id, policy_id, version, effective_from, source_text, "
        "source_sha256) VALUES (:o, :p, :ver, '2026-01-01', :t, :h) RETURNING id"),
        {"o": org, "p": policy, "ver": POLICY_VERSION, "t": POLICY_TEXT, "h": hashlib.sha256(POLICY_TEXT.encode()).hexdigest()}
    ).scalar_one()
    rules = {}
    for r in RULES:
        rules[r["code"]] = _exec(conn,
            "INSERT INTO policy_rules (organization_id, policy_version_id, code, title, title_ar, requirement, "
            "requirement_ar, spec) VALUES (:o, :v, :c, :t, :ta, :r, :ra, :spec) RETURNING id",
            {"o": org, "v": version, "c": r["code"], "t": r["title"], "ta": r["title_ar"], "r": r["requirement"],
             "ra": r["requirement_ar"], "spec": r["spec"]}, "spec").scalar_one()
    conn.execute(text(
        "INSERT INTO price_lists (organization_id, payer_id, service_code, description, price_sar) "
        "VALUES (:o, :p, :c, 'MRI lumbar spine without contrast (illustrative demo price)', :v)"),
        {"o": org, "p": payers["DPA"], "c": MRI_LUMBAR_CODE, "v": MRI_LUMBAR_PRICE_SAR})
    for code, display, cat in (("DEN-STEP-04", "Step therapy requirements not met (demo)", "clinical"),
                               ("DEN-DOC-01", "Insufficient clinical documentation (demo)", "documentation")):
        conn.execute(text("INSERT INTO denial_reasons (organization_id, code, display, category) "
                          "VALUES (:o, :c, :d, :k)"), {"o": org, "c": code, "d": display, "k": cat})
    return {"payers": payers, "facility": facility, "rules": rules, "facilities": {}}


def _patient(conn: Connection, org: str, ref: str, name: str, birth_year: int | None, gender: str) -> Any:
    return conn.execute(text(
        "INSERT INTO patients (organization_id, external_ref, display_name, birth_year, gender) "
        "VALUES (:o, :r, :n, :b, :g) RETURNING id"),
        {"o": org, "r": ref, "n": name, "b": birth_year, "g": gender}).scalar_one()


def _request(conn: Connection, ctx: dict[str, Any], org: str, **f: Any) -> Any:
    rid = _exec(conn,
        """INSERT INTO authorization_requests (organization_id, case_number, legacy_id, patient_id, facility_id,
           payer_id, physician_name, specialty, requested_service, requested_service_ar, service_code,
           diagnosis_code, diagnosis_display, financial_value_sar, status, clinical_note, data_source, extra,
           requested_on)
           VALUES (:o, :case_number, :legacy_id, :patient_id, :facility_id, :payer_id, :physician, :specialty,
           :service, :service_ar, :service_code, :dx_code, :dx_display, :value, :status, :note, :source,
           :extra, :requested_on) RETURNING id""",
        {"o": org, **f, "extra": f.get("extra") or {}}, "extra").scalar_one()
    conn.execute(text(
        "INSERT INTO authorization_events (organization_id, authorization_request_id, occurred_at, from_status, "
        "to_status, actor, note) VALUES (:o, :id, :t, NULL, :s, 'system:seed', 'seeded')"),
        {"o": org, "id": rid, "t": datetime.combine(f["requested_on"], datetime.min.time(), UTC), "s": f["status"]})
    return rid


def _load_legacy_case(conn: Connection, ctx: dict[str, Any], c: dict[str, Any]) -> None:
    org = DEMO_ORG_ID
    _bind(conn, org)
    fac_en, fac_ar = _split(c["facilityName"])
    fac = ctx["facilities"].get(fac_en)
    if fac is None:
        fac = conn.execute(text(
            "INSERT INTO facilities (organization_id, code, name, name_ar) VALUES (:o, :c, :n, :a) RETURNING id"),
            {"o": org, "c": f"LEGACY-{len(ctx['facilities']) + 1}", "n": fac_en, "a": fac_ar}).scalar_one()
        ctx["facilities"][fac_en] = fac
    name_en, name_ar = _split(c["patientName"])
    requested_on = date.fromisoformat(c["createdDate"])
    pid = _patient(conn, org, c["patientId"], f"{name_ar} / {name_en}" if name_ar else name_en,
                   requested_on.year - int(c["age"]), c["gender"])
    rule_code_by_id = {r["id"]: r["code"] for r in c["policyRules"]}
    extra: dict[str, Any] = {}
    if c.get("discoverableEvidence"):
        d = dict(c["discoverableEvidence"])
        d["satisfiesRuleIds"] = [rule_code_by_id.get(x, x) for x in d.get("satisfiesRuleIds", [])]
        extra["discoverable_evidence"] = d
    rid = _request(conn, ctx, org, case_number=c["claimNumber"], legacy_id=c["id"], patient_id=pid,
                   facility_id=fac, payer_id=ctx["payers"][c["payerCode"][:3]], physician=c["doctorName"],
                   specialty=c["specialty"], service=c["requestedService"], service_ar=c["requestedServiceAr"],
                   service_code=c["cptCode"], dx_code=c["icd10Code"],
                   dx_display=(c["fhirPayload"].get("diagnosisCodes") or [{}])[0].get("display"),
                   value=c["revenueRisk"]["financialValue"], status=c["status"], note=c["clinicalNoteText"],
                   source="legacy-demo", extra=extra, requested_on=requested_on)

    rs = c["readinessScore"]
    conn.execute(text(
        """INSERT INTO readiness_scores (organization_id, authorization_request_id, computed_at, clinical_evidence,
           policy_match, documentation, coding_integrity, required_attachments, administrative_completeness,
           overall_score, label, label_ar, warning, warning_ar, method)
           VALUES (:o, :id, :t, :a, :b, :c, :d, :e, :f, :g, :l, :la, :w, :wa, 'demo-data')"""),
        {"o": org, "id": rid, "t": _ts(c["auditTrail"][0]["timestamp"]), "a": rs["clinicalEvidence"],
         "b": rs["policyMatch"], "c": rs["documentation"], "d": rs["codingIntegrity"], "e": rs["requiredAttachments"],
         "f": rs["administrativeCompleteness"], "g": rs["overallScore"], "l": rs["readinessLabel"],
         "la": rs["readinessLabelAr"], "w": rs.get("warningNotice"), "wa": rs.get("warningNoticeAr")})
    rr = c["revenueRisk"]
    conn.execute(text(
        """INSERT INTO revenue_risk (organization_id, authorization_request_id, computed_at, financial_value_sar,
           denial_risk_pct, revenue_at_risk_sar, recoverable_value_sar, priority)
           VALUES (:o, :id, :t, :v, :p, :ar, :rec, :pr)"""),
        {"o": org, "id": rid, "t": _ts(c["auditTrail"][0]["timestamp"]), "v": rr["financialValue"],
         "p": rr["denialRiskPercentage"], "ar": rr["revenueAtRisk"], "rec": rr["recoverableValue"],
         "pr": rr["priority"]})
    for i, f in enumerate(c["clinicalFacts"]):
        conn.execute(text(
            """INSERT INTO clinical_facts (organization_id, authorization_request_id, category, fact, fact_ar,
               source_label, fact_date, confidence, ord) VALUES (:o, :id, :c, :f, :fa, :s, :d, :conf, :i)"""),
            {"o": org, "id": rid, "c": f["category"], "f": f["fact"], "fa": f["factAr"], "s": f["source"],
             "d": date.fromisoformat(f["date"]), "conf": f["confidence"], "i": i})
    for i, r in enumerate(c["policyRules"]):
        conn.execute(text(
            """INSERT INTO authorization_requirements (organization_id, authorization_request_id, policy_rule_id,
               code, title, title_ar, requirement, requirement_ar, status, evidence_source, ord)
               VALUES (:o, :id, :rule, :c, :t, :ta, :r, :ra, :s, :es, :i)"""),
            {"o": org, "id": rid, "rule": ctx["rules"].get(r["code"]), "c": r["code"], "t": r["title"],
             "ta": r["titleAr"], "r": r["requirement"], "ra": r["requirementAr"], "s": r["status"],
             "es": r.get("evidenceSource"), "i": i})
    for i, e in enumerate(c["evidenceItems"]):
        conn.execute(text(
            """INSERT INTO authorization_evidence (organization_id, authorization_request_id, requirement,
               requirement_ar, status, matched_fact, source_label, evidence_date, confidence, ord)
               VALUES (:o, :id, :r, :ra, :s, :m, :src, :d, :c, :i)"""),
            {"o": org, "id": rid, "r": e["requirement"], "ra": e["requirementAr"], "s": e["status"],
             "m": e.get("matchedFact"), "src": e.get("sourceEncounter"),
             "d": date.fromisoformat(e["date"]) if e.get("date") else None, "c": e["confidence"], "i": i})
    for a in c["agentRuns"]:
        _exec(conn,
            """INSERT INTO agent_runs (organization_id, authorization_request_id, agent_id, name, name_ar, status,
               output_summary, output_summary_ar, model, prompt_version, output, latency_ms, started_at)
               VALUES (:o, :id, :a, :n, :na, :s, :os, :osa, 'demo-data', 'n/a', :out, :ms, :t)""",
            {"o": org, "id": rid, "a": a["agentId"], "n": a["name"], "na": a["nameAr"], "s": a["status"],
             "os": a["outputSummary"], "osa": a["outputSummaryAr"], "out": {}, "ms": a["durationMs"],
             "t": _ts(a["timestamp"])}, "out")
    raw = json.loads(c["fhirPayload"]["rawJson"])
    _exec(conn,
        """INSERT INTO nphies_transactions (organization_id, authorization_request_id, direction, resource_type,
           simulated, validated, payload) VALUES (:o, :id, :d, :rt, true, false, :p)""",
        {"o": org, "id": rid, "d": "INBOUND" if raw.get("resourceType") == "ClaimResponse" else "OUTBOUND",
         "rt": raw.get("resourceType", "Claim"), "p": c["fhirPayload"]}, "p")
    if c.get("appealPackage"):
        ap = c["appealPackage"]
        den = conn.execute(text(
            """INSERT INTO denials (organization_id, authorization_request_id, reason_code, reason, reason_ar,
               root_cause, root_cause_ar, missing_requirement, missing_requirement_ar, simulated)
               VALUES (:o, :id, 'DEN-STEP-04', :r, :ra, :rc, :rca, :m, :ma, true) RETURNING id"""),
            {"o": org, "id": rid, "r": ap["denialReason"], "ra": ap["denialReasonAr"], "rc": ap["rootCause"],
             "rca": ap["rootCauseAr"], "m": ap["missingRequirement"], "ma": ap["missingRequirementAr"]}).scalar_one()
        app_id = conn.execute(text(
            """INSERT INTO appeals (organization_id, authorization_request_id, denial_id, status, strategy,
               strategy_ar, letter_en, letter_ar, strength) VALUES (:o, :id, :d, 'DRAFT', :s, :sa, :le, :la, :st)
               RETURNING id"""),
            {"o": org, "id": rid, "d": den, "s": ap["appealStrategy"], "sa": ap["appealStrategyAr"],
             "le": ap["formalLetterEn"], "la": ap["formalLetterAr"], "st": ap["appealStrength"]}).scalar_one()
        for i, e in enumerate(ap["foundEvidence"]):
            conn.execute(text(
                """INSERT INTO appeal_evidence (organization_id, appeal_id, fact, fact_ar, source_label,
                   evidence_date, ord) VALUES (:o, :a, :f, :fa, :s, :d, :i)"""),
                {"o": org, "a": app_id, "f": e["fact"], "fa": e["factAr"], "s": e["source"],
                 "d": date.fromisoformat(e["date"]) if e.get("date") else None, "i": i})
        conn.execute(text(
            "INSERT INTO recovery_cases (organization_id, authorization_request_id, denial_id, status, "
            "recoverable_value_sar) VALUES (:o, :id, :d, 'OPEN', :v)"),
            {"o": org, "id": rid, "d": den, "v": rr["recoverableValue"]})
    if c["status"] in ("RISK_DETECTED",):
        conn.execute(text(
            "INSERT INTO authorization_events (organization_id, authorization_request_id, from_status, to_status, "
            "actor, note) VALUES (:o, :id, 'DRAFT', 'RISK_DETECTED', 'system:seed', 'legacy demo state')"),
            {"o": org, "id": rid})
    for e in c["auditTrail"]:
        audit.append(conn, org_id=org, chain_key=str(rid), actor=SEED_ACTOR, action="legacy.event",
                     details={"message": e["action"], "message_ar": e["actionAr"], "actor_label": e["actor"],
                              "simulated": "Payer" in e["actor"] or "NPHIES" in e["action"]},
                     occurred_at=_ts(e["timestamp"]))


def _load_bundle(conn: Connection, ctx: dict[str, Any], bundle: dict[str, Any]) -> None:
    org = DEMO_ORG_ID
    _bind(conn, org)
    res = [e["resource"] for e in bundle["entry"]]
    by_type: dict[str, list[dict[str, Any]]] = {}
    for r in res:
        by_type.setdefault(r["resourceType"], []).append(r)
    patient = by_type["Patient"][0]
    pid = _patient(conn, org, patient["id"], patient["name"][0]["text"], int(patient["birthDate"][:4]),
                   "F" if patient["gender"] == "female" else "M")
    enc_ids = {}
    for enc in by_type.get("Encounter", []):
        enc_ids[enc["id"]] = conn.execute(text(
            """INSERT INTO encounters (organization_id, patient_id, facility_id, encounter_ref, kind, started_on)
               VALUES (:o, :p, :f, :r, :k, :d) RETURNING id"""),
            {"o": org, "p": pid, "f": ctx["facility"], "r": enc["id"], "k": enc["type"][0]["text"],
             "d": date.fromisoformat(enc["period"]["start"])}).scalar_one()
    index_note = ""
    sr = by_type["ServiceRequest"][0]
    index_enc = sr["encounter"]["reference"].split("/", 1)[1]
    for doc in by_type.get("DocumentReference", []):
        att = doc["content"][0]["attachment"]
        content = base64.b64decode(att["data"]).decode("utf-8")
        enc_ref = doc["context"]["encounter"][0]["reference"].split("/", 1)[1]
        doc_id = conn.execute(text(
            """INSERT INTO clinical_documents (organization_id, patient_id, encounter_id, doc_ref, doc_type, language,
               authored_on, content, content_sha256) VALUES (:o, :p, :e, :r, :t, :l, :d, :c, :h) RETURNING id"""),
            {"o": org, "p": pid, "e": enc_ids.get(enc_ref), "r": doc["id"], "t": doc["type"]["text"],
             "l": att.get("language", "en"), "d": date.fromisoformat(doc["date"][:10]), "c": content,
             "h": hashlib.sha256(content.encode()).hexdigest()}).scalar_one()
        for c in chunk(content):
            conn.execute(text(
                "INSERT INTO document_chunks (organization_id, document_id, ord, char_start, char_end, content) "
                "VALUES (:o, :d, :i, :s, :e, :c)"),
                {"o": org, "d": doc_id, "i": c.ord, "s": c.start, "e": c.end, "c": c.text})
        if enc_ref == index_enc:
            index_note = content
    cond = by_type["Condition"][0]["code"]["coding"][0]
    svc = sr["code"]["coding"][0]
    rid = _request(conn, ctx, org, case_number=bundle["id"], legacy_id=None, patient_id=pid,
                   facility_id=ctx["facility"], payer_id=ctx["payers"]["DPA"], physician="Synthetic Orthopedic Clinic",
                   specialty="Orthopedic Surgery", service="MRI Lumbar Spine", service_ar="رنين مغناطيسي للفقرات القطنية",
                   service_code=svc["code"], dx_code=cond["code"], dx_display=cond["display"],
                   value=MRI_LUMBAR_PRICE_SAR, status="DRAFT", note=index_note, source="synthetic",
                   requested_on=date.fromisoformat(sr["authoredOn"]))
    for i, r in enumerate(RULES):
        conn.execute(text(
            """INSERT INTO authorization_requirements (organization_id, authorization_request_id, policy_rule_id,
               code, title, title_ar, requirement, requirement_ar, status, ord)
               VALUES (:o, :id, :rule, :c, :t, :ta, :r, :ra, 'PENDING', :i)"""),
            {"o": org, "id": rid, "rule": ctx["rules"][r["code"]], "c": r["code"], "t": r["title"],
             "ta": r["title_ar"], "r": r["requirement"], "ra": r["requirement_ar"], "i": i})
    audit.append(conn, org_id=org, chain_key=str(rid), actor=SEED_ACTOR, action="case.ingested",
                 details={"message": f"Synthetic FHIR bundle {bundle['id']} ingested "
                                     f"({len(by_type.get('DocumentReference', []))} documents).",
                          "message_ar": f"تم استيراد حزمة FHIR اصطناعية {bundle['id']}.",
                          "actor_label": "Seeder", "bundle": bundle["id"]},
                 occurred_at=datetime.combine(date.fromisoformat(sr["authoredOn"]), datetime.min.time(), UTC))
