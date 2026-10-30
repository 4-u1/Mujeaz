"""M3: documentation queries, physician addenda, automatic re-analysis and what-if = reality."""

import json
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

from app.ai.router import limiter
from app.cli import run_seed
from app.db import get_owner_engine

ROOT = Path(__file__).resolve().parents[3]
ANN = {json.loads(line)["case_id"]: json.loads(line)
       for line in (ROOT / "evals/data/mri_lumbar/annotations.jsonl").open(encoding="utf-8")}
R1 = "R1_conservative_therapy_6w"
FIXABLE = [c for c, a in ANN.items() if a["expected"]["requirements"][R1]["rule"] != "PASSED"]


@pytest.fixture(scope="module", autouse=True)
def fresh_state(database: None, login) -> Iterator[None]:  # type: ignore[no-untyped-def]
    yield
    run_seed(reset=True)
    login.cache.clear()


def _ids(client, h) -> dict[str, str]:  # type: ignore[no-untyped-def]
    return {c["caseNumber"]: c["id"] for c in client.get("/api/cases", params={"limit": 500}, headers=h).json()["items"]}


def _answer(case: str, weeks: int = 9, sessions: int = 10) -> dict:  # type: ignore[type-arg]
    end = date.fromisoformat(ANN[case]["requested_on"]) - timedelta(days=1)
    return {"answer": {"kind": "therapy", "start_date": (end - timedelta(weeks=weeks)).isoformat(),
                       "end_date": end.isoformat(), "sessions": sessions, "provider": "Demo Physio Clinic"},
            "language": "ar" if ANN[case]["language"] == "ar" else "en"}


def _post(client, url: str, h, **kw):  # type: ignore[no-untyped-def]
    limiter._hits.clear()
    return client.post(url, headers=h, **kw)


def _open_query(client, h, cid: str) -> dict:  # type: ignore[no-untyped-def,type-arg]
    items = client.get("/api/queries", params={"case_id": cid}, headers=h).json()["items"]
    assert len(items) == 1, items
    return items[0]


def test_what_if_equals_reality_for_every_fixable_case(client, login) -> None:  # type: ignore[no-untyped-def]
    officer, doctor = login("sara.auth"), login("dr.khalid")
    ids = _ids(client, officer)
    assert len(FIXABLE) >= 15
    for case in FIXABLE:
        cid = ids[case]
        assert _post(client, f"/api/cases/{cid}/analyze", officer, params={"mode": "baseline"}).status_code == 200
        q = _open_query(client, doctor, cid)
        assert q["requirementId"] == R1 and q["status"] == "OPEN"

        sim = _post(client, f"/api/cases/{cid}/what-if", officer, json=_answer(case))
        assert sim.status_code == 200, sim.text
        sim_body = sim.json()
        assert sim_body["simulation"] is True and sim_body["before"]["status"] == "RISK_DETECTED"

        real = _post(client, f"/api/queries/{q['id']}/answer", doctor, json=_answer(case))
        assert real.status_code == 200, (case, real.text)
        analysis = real.json()["analysis"]
        after = sim_body["after"]
        assert analysis["status"] == after["status"], case
        assert analysis["readiness"] == after["readiness"], case
        assert {k: v for k, v in analysis["outcomes"].items() if k in after["evidence"]} == after["evidence"], case
        expected = "MISSING" if ANN[case]["expected"]["contradiction"] else "FOUND"
        assert after["evidence"][R1] == expected, case


def test_what_if_does_not_persist(client, login) -> None:  # type: ignore[no-untyped-def]
    h = login("sara.auth")
    case = next(c for c in FIXABLE if c not in ("SYN-MRI-001",) and ANN[c]["scenario"] == "missing")
    cid = _ids(client, h)[case]
    with get_owner_engine().begin() as conn:
        before = conn.execute(text("SELECT (SELECT count(*) FROM analysis_runs), (SELECT count(*) FROM clinical_documents), "
                                   "(SELECT count(*) FROM audit_logs)")).one()
    assert _post(client, f"/api/cases/{cid}/what-if", login("omar.coder"), json=_answer(case)).status_code == 200
    with get_owner_engine().begin() as conn:
        after = conn.execute(text("SELECT (SELECT count(*) FROM analysis_runs), (SELECT count(*) FROM clinical_documents), "
                                  "(SELECT count(*) FROM audit_logs)")).one()
    assert tuple(before) == tuple(after)


def test_full_loop_to_the_submission_gate(client, login) -> None:  # type: ignore[no-untyped-def]
    """Runs after the what-if test above, which answered the query of every fixable case."""
    officer, auditor = login("sara.auth"), login("noura.audit")
    case = next(c for c in FIXABLE if ANN[c]["scenario"] == "partial_duration")
    cid = _ids(client, officer)[case]
    twin = client.get(f"/api/cases/{cid}", headers=officer).json()
    assert twin["status"] == "DECISION_READY"
    assert twin["readinessExplanation"]["overall"] == twin["readinessScore"]["overallScore"] == 100
    assert any(f.get("postRequestAddendum") for f in twin["clinicalFacts"])
    assert [q["status"] for q in twin["documentationQueries"]] == ["ANSWERED"]
    assert twin["documentationQueries"][0]["addendumRef"] == f"{case}-ADD1"
    r = _post(client, f"/api/cases/{cid}/transitions", officer, json={"to": "SUBMITTED", "note": "reviewed"})
    assert r.status_code == 200
    actions = [e["action"] for e in client.get(f"/api/audit/{cid}", headers=auditor).json()["entries"]]
    assert actions[:2] == ["case.ingested", "case.analyzed"]
    for a in ("cdi.query_opened", "cdi.query_answered", "case.transition"):
        assert a in actions
    assert actions.count("case.analyzed") == 2  # officer's analysis + automatic re-analysis after the addendum
    assert client.get(f"/api/audit/{cid}/verify", headers=auditor).json()["valid"] is True


def test_queue_and_document_viewer(client, login) -> None:  # type: ignore[no-untyped-def]
    h = login("sara.auth")
    body = client.get("/api/queue", headers=h).json()
    items = body["items"]
    assert body["formula"].startswith("amount")
    assert [i["priority"] for i in items] == sorted((i["priority"] for i in items), reverse=True)
    assert all(i["status"] in ("DRAFT", "RISK_DETECTED", "EVIDENCE_SEARCHING", "DECISION_READY") for i in items)
    unanalyzed = next(i for i in items if not i["analyzed"])
    assert unanalyzed["amountBasis"] == "full_value" and unanalyzed["nextAction"] == "Analyze"

    case = next(c for c in FIXABLE if ANN[c]["scenario"] == "missing")
    cid = _ids(client, h)[case]
    docs = client.get(f"/api/cases/{cid}/documents", headers=h).json()
    by_ref = {d["docRef"]: d for d in docs["documents"]}
    addendum = by_ref[f"{case}-ADD1"]
    assert addendum["postRequestAddendum"] is True and addendum["signedAt"]
    assert docs["documents"][-1]["docRef"] == f"{case}-ADD1"  # addenda listed after the record
    for f in docs["facts"]:
        assert by_ref[f["docRef"]]["content"][f["start"]:f["end"]]
        assert f["utf16End"] >= f["end"]
    assert docs["retrieved"][R1]
    assert client.get("/api/cases/00000000-0000-4000-8000-00000000ffff/documents", headers=h).status_code == 404


def test_query_permissions_validation_and_decline(client, login) -> None:  # type: ignore[no-untyped-def]
    run_seed(reset=True)
    login.cache.clear()
    officer, doctor = login("sara.auth"), login("dr.khalid")
    case = next(c for c in FIXABLE if ANN[c]["scenario"] == "missing")
    cid = _ids(client, officer)[case]
    assert _post(client, f"/api/cases/{cid}/analyze", officer, params={"mode": "baseline"}).status_code == 200
    q = _open_query(client, doctor, cid)
    url = f"/api/queries/{q['id']}/answer"
    assert _post(client, url, officer, json=_answer(case)).status_code == 403  # officers do not author documentation
    assert _post(client, url, login("omar.coder"), json=_answer(case)).status_code == 403
    assert _post(client, url, login("other.auth"), json=_answer(case)).status_code == 403
    late = _answer(case)
    late["answer"]["end_date"] = (date.fromisoformat(ANN[case]["requested_on"]) + timedelta(days=3)).isoformat()
    assert _post(client, url, doctor, json=late).status_code == 422
    free = {"answer": {"kind": "free_text", "text": "trust me"}}
    assert _post(client, url, doctor, json=free).status_code == 422
    r = _post(client, f"/api/queries/{q['id']}/decline", doctor, json={"reason": "No therapy was given"})
    assert r.status_code == 200
    assert _post(client, url, doctor, json=_answer(case)).status_code == 409  # closed
    twin = client.get(f"/api/cases/{cid}", headers=officer).json()
    assert twin["status"] == "RISK_DETECTED"
    assert twin["documentationQueries"][0]["status"] == "DECLINED"


def test_query_is_withdrawn_when_evidence_appears_elsewhere(client, login) -> None:  # type: ignore[no-untyped-def]
    officer = login("sara.auth")
    case = next(c for c in FIXABLE if ANN[c]["scenario"] == "partial_duration")
    cid = _ids(client, officer)[case]
    assert _post(client, f"/api/cases/{cid}/analyze", officer, params={"mode": "baseline"}).status_code == 200
    _open_query(client, officer, cid)
    with get_owner_engine().begin() as conn:  # a late-arriving physiotherapy report filed by the clinic
        conn.execute(text(
            "INSERT INTO clinical_documents (organization_id, patient_id, doc_ref, doc_type, language, authored_on, "
            "content, content_sha256, authorization_request_id) SELECT organization_id, patient_id, :r, 'addendum', 'en', "
            "requested_on, :c, repeat('0', 64), id FROM authorization_requests WHERE id = :id"),
            {"r": f"{case}-PT-LATE", "c": "Completed physiotherapy: 10 sessions over 8 weeks.", "id": cid})
    assert _post(client, f"/api/cases/{cid}/analyze", officer, params={"mode": "baseline"}).status_code == 200
    statuses = [q["status"] for q in client.get(f"/api/cases/{cid}", headers=officer).json()["documentationQueries"]]
    assert statuses == ["WITHDRAWN"]
