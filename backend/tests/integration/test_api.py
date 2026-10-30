from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import text

from app.audit import service as audit
from app.audit.service import Actor
from app.db import get_engine, get_owner_engine
from app.seed.constants import DEMO_ORG_ID


def _case_id(client, headers, number: str) -> str:  # type: ignore[no-untyped-def]
    r = client.get("/api/cases", params={"q": number}, headers=headers)
    assert r.status_code == 200, r.text
    items = [c for c in r.json()["items"] if c["caseNumber"] == number]
    assert items, number
    return items[0]["id"]


def test_health(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/healthz").json()["status"] == "ok"
    assert client.get("/readyz").status_code == 200


def test_auth_required(client) -> None:  # type: ignore[no-untyped-def]
    r = client.get("/api/cases")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "http_401"
    assert client.get("/api/cases", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_unknown_user_cannot_log_in(client) -> None:  # type: ignore[no-untyped-def]
    assert client.post("/api/auth/dev-login", json={"username": "ghost.user"}).status_code == 401


def test_me_lists_permissions(client, login) -> None:  # type: ignore[no-untyped-def]
    me = client.get("/api/auth/me", headers=login("noura.audit")).json()
    assert me["roles"] == ["auditor"]
    assert "audit:read" in me["permissions"] and "case:approve_submission" not in me["permissions"]


def test_jwks_published(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/.well-known/jwks.json").json()["keys"][0]["kty"] == "RSA"


def test_cases_are_listed_from_the_database(client, login) -> None:  # type: ignore[no-untyped-def]
    body = client.get("/api/cases", params={"limit": 500}, headers=login("sara.auth")).json()
    assert body["total"] == 73
    numbers = {c["caseNumber"] for c in body["items"]}
    assert {"AUTH-2026-4922", "AUTH-2026-8103", "AUTH-2026-3109", "SYN-MRI-001"} <= numbers
    assert "OTHER-0001" not in numbers


def test_tenant_isolation_via_api(client, login) -> None:  # type: ignore[no-untyped-def]
    other = client.get("/api/cases", headers=login("other.auth")).json()
    assert [c["caseNumber"] for c in other["items"]] == ["OTHER-0001"]
    demo_case = _case_id(client, login("sara.auth"), "AUTH-2026-4922")
    assert client.get(f"/api/cases/{demo_case}", headers=login("other.auth")).status_code == 404


def test_tenant_isolation_in_the_database() -> None:
    with get_engine().begin() as conn:
        assert conn.execute(text("SELECT count(*) FROM authorization_requests")).scalar_one() == 0
        conn.execute(text("SELECT set_config('app.org_id', :o, true)"), {"o": DEMO_ORG_ID})
        assert conn.execute(text("SELECT count(*) FROM authorization_requests")).scalar_one() == 73


def test_twin_shape_for_legacy_case(client, login) -> None:  # type: ignore[no-untyped-def]
    h = login("sara.auth")
    twin = client.get(f"/api/cases/{_case_id(client, h, 'AUTH-2026-4922')}", headers=h).json()
    assert twin["legacyId"] == "case-4922" and twin["status"] == "RISK_DETECTED"
    assert twin["revenueRisk"]["financialValue"] == 2800
    assert twin["readinessScore"]["overallScore"] == 74
    assert twin["fhirPayload"]["resourceType"] == "Claim"
    assert len(twin["agentRuns"]) == 6 and twin["auditTrail"]
    assert twin["discoverableEvidence"]["satisfiesRuleIds"] == ["DPA-LUMBAR-POL-04"]


def test_synthetic_case_is_not_analyzed_yet(client, login) -> None:  # type: ignore[no-untyped-def]
    h = login("sara.auth")
    twin = client.get(f"/api/cases/{_case_id(client, h, 'SYN-MRI-001')}", headers=h).json()
    assert twin["analyzed"] is False and twin["status"] == "DRAFT"
    assert {r["status"] for r in twin["policyRules"]} == {"PENDING"}


def test_permissions_on_transitions(client, login) -> None:  # type: ignore[no-untyped-def]
    cid = _case_id(client, login("sara.auth"), "SYN-MRI-002")
    r = client.post(f"/api/cases/{cid}/transitions", json={"to": "SUBMITTED"}, headers=login("sara.auth"))
    assert r.status_code == 409  # DRAFT → SUBMITTED is not allowed
    r = client.post(f"/api/cases/{cid}/transitions", json={"to": "RISK_DETECTED"}, headers=login("dr.khalid"))
    assert r.status_code == 403


def test_end_to_end_legacy_flow_with_human_gate(client, login) -> None:  # type: ignore[no-untyped-def]
    h = login("sara.auth")
    cid = _case_id(client, h, "AUTH-2026-4922")
    r = client.post(f"/api/cases/{cid}/evidence-hunter/demo", headers=h).json()
    assert r["found"] is True and r["status"] == "DECISION_READY" and r["overallScore"] == 98
    assert r["revenueProtected"] == 2184 - 140
    again = client.post(f"/api/cases/{cid}/evidence-hunter/demo", headers=h).json()
    assert again["found"] is False  # evidence is consumed once
    r = client.post(f"/api/cases/{cid}/transitions", json={"to": "SUBMITTED", "note": "reviewed"}, headers=h)
    assert r.status_code == 200, r.text
    with get_owner_engine().begin() as conn:
        gate = conn.execute(text("SELECT gate FROM human_reviews WHERE authorization_request_id = :i"),
                            {"i": cid}).scalar_one()
    assert gate == "SUBMISSION"
    v = client.get(f"/api/audit/{cid}/verify", headers=login("noura.audit")).json()
    assert v["valid"] is True and v["entries"] >= 4


def test_audit_requires_permission(client, login) -> None:  # type: ignore[no-untyped-def]
    cid = _case_id(client, login("sara.auth"), "SYN-MRI-003")
    assert client.get(f"/api/audit/{cid}", headers=login("omar.coder")).status_code == 403
    assert client.get(f"/api/audit/{cid}", headers=login("noura.audit")).status_code == 200


def test_audit_tampering_is_detected(client, login) -> None:  # type: ignore[no-untyped-def]
    h = login("sara.auth")
    cid = _case_id(client, h, "SYN-MRI-050")
    for to in ("RISK_DETECTED", "EVIDENCE_SEARCHING"):
        assert client.post(f"/api/cases/{cid}/transitions", json={"to": to}, headers=h).status_code == 200
    auditor = login("noura.audit")
    assert client.get(f"/api/audit/{cid}/verify", headers=auditor).json()["valid"] is True
    with get_owner_engine().begin() as conn:
        conn.execute(text("ALTER TABLE audit_logs DISABLE TRIGGER audit_logs_no_update"))
        conn.execute(text("UPDATE audit_logs SET details = jsonb_set(details, '{to}', '\"APPROVED\"') "
                          "WHERE chain_key = :k AND seq = 2"), {"k": cid})
        conn.execute(text("ALTER TABLE audit_logs ENABLE TRIGGER audit_logs_no_update"))
    v = client.get(f"/api/audit/{cid}/verify", headers=auditor).json()
    assert v["valid"] is False and v["first_broken_seq"] == 2


def test_audit_rows_cannot_be_updated_by_the_app_role(client, login) -> None:  # type: ignore[no-untyped-def]
    with get_engine().connect() as conn:
        conn.execute(text("SELECT set_config('app.org_id', :o, false)"), {"o": DEMO_ORG_ID})
        try:
            conn.execute(text("UPDATE audit_logs SET action = 'x'"))
            raise AssertionError("update should be rejected")
        except Exception as exc:  # noqa: BLE001
            assert "permission denied" in str(exc)
        conn.rollback()


def test_concurrent_appends_keep_one_chain(client, login) -> None:  # type: ignore[no-untyped-def]
    cid = _case_id(client, login("sara.auth"), "SYN-MRI-049")

    def write(i: int) -> None:
        with get_engine().begin() as conn:
            conn.execute(text("SELECT set_config('app.org_id', :o, true)"), {"o": DEMO_ORG_ID})
            audit.append(conn, org_id=DEMO_ORG_ID, chain_key=cid, actor=Actor("test", "system"),
                         action="test.concurrent", details={"i": i})

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(24)))
    v = client.get(f"/api/audit/{cid}/verify", headers=login("noura.audit")).json()
    assert v["valid"] is True and v["entries"] == 25  # 1 seeded + 24


def test_metrics_are_computed(client, login) -> None:  # type: ignore[no-untyped-def]
    m = client.get("/api/metrics", headers=login("faisal.rcm")).json()
    assert m["totalCases"] == 73 and m["recoveryQueueCount"] >= 1
    assert client.get("/api/metrics", headers=login("dr.khalid")).status_code == 403


def test_ai_fallback_is_labelled_and_has_no_facts(client, login) -> None:  # type: ignore[no-untyped-def]
    r = client.post("/api/ai/analyze-order", json={"clinicalNoteText": "MRI lumbar requested"},
                    headers=login("sara.auth")).json()
    assert r["mode"] == "fallback" and r["clinicalFacts"] == [] and r["notice"]
    assert r["readinessScore"]["overallScore"] <= 60 or r["scoring"]["method"] == "deterministic-v1"
    a = client.post("/api/ai/generate-appeal", json={"claimNumber": "X"}, headers=login("lama.appeals")).json()
    assert a["mode"] == "fallback"
    assert client.post("/api/ai/generate-appeal", json={}, headers=login("sara.auth")).status_code == 403


def test_validation_errors_use_the_error_envelope(client, login) -> None:  # type: ignore[no-untyped-def]
    r = client.post("/api/ai/analyze-order", json={"clinicalNoteText": ""}, headers=login("sara.auth"))
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_twins_use_a_constant_number_of_queries(client, login) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import event

    engine = get_engine()
    statements: list[str] = []

    def record(conn, cursor, statement, *args):  # type: ignore[no-untyped-def]
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        r = client.get("/api/twins", headers=login("sara.auth"))
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert r.status_code == 200 and len(r.json()["items"]) == 73
    assert len(statements) <= 15, f"{len(statements)} queries for 73 cases"


def test_batched_twin_matches_single_twin(client, login) -> None:  # type: ignore[no-untyped-def]
    h = login("sara.auth")
    twins = {t["id"]: t for t in client.get("/api/twins", headers=h).json()["items"]}
    for number in ("AUTH-2026-8103", "AUTH-2026-3109", "SYN-MRI-010"):
        cid = _case_id(client, h, number)
        assert client.get(f"/api/cases/{cid}", headers=h).json() == twins[cid]
    assert twins[_case_id(client, h, "AUTH-2026-8103")]["appealPackage"]["foundEvidence"]


def test_dev_login_is_disabled_when_dev_auth_is_off(client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.config import Settings

    monkeypatch.setattr("app.auth_router.get_settings", lambda: Settings(_env_file=None, dev_auth=False))
    assert client.post("/api/auth/dev-login", json={"username": "sara.auth"}).status_code == 404
    assert client.get("/api/auth/dev-users").status_code == 404
