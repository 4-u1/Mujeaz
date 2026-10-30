"""M2: the analysis pipeline through the API, against every synthetic case and its ground truth."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import text

from app.ai.router import limiter
from app.cli import run_seed
from app.db import get_engine, get_owner_engine
from app.seed.constants import DEMO_ORG_ID

ROOT = Path(__file__).resolve().parents[3]
ANNOTATIONS = {json.loads(line)["case_id"]: json.loads(line)
               for line in (ROOT / "evals/data/mri_lumbar/annotations.jsonl").open(encoding="utf-8")}
RULE_CODE = {"R1_conservative_therapy_6w": "DPA-LUMBAR-POL-04", "R2_diagnosis_procedure_compatibility": "DPA-CODING-01"}


@pytest.fixture(scope="module", autouse=True)
def fresh_state(database: None) -> Iterator[None]:
    """Analysis changes case state; reseed afterwards so other modules see the pristine dataset."""
    yield
    run_seed(reset=True)


def _ids(client, headers) -> dict[str, str]:  # type: ignore[no-untyped-def]
    body = client.get("/api/cases", params={"limit": 500}, headers=headers).json()
    return {c["claimNumber"]: c["id"] for c in body["items"]}


def _analyze(client, cid: str, headers, **params):  # type: ignore[no-untyped-def]
    limiter._hits.clear()
    return client.post(f"/api/cases/{cid}/analyze", params={"mode": "baseline", **params}, headers=headers)


def test_every_synthetic_case_matches_ground_truth(client, login) -> None:  # type: ignore[no-untyped-def]
    h = login("sara.auth")
    ids = _ids(client, h)
    seen: set[str] = set()
    for case_id, ann in ANNOTATIONS.items():
        r = _analyze(client, ids[case_id], h)
        assert r.status_code == 200, (case_id, r.text)
        body = r.json()
        assert body["mode"] == "baseline"
        assert body["policy_version"] == "DPA-LUMBAR-POL@2026.1"
        for rid, exp in ann["expected"]["requirements"].items():
            if "evidence" in exp:
                assert body["outcomes"][rid] == exp["evidence"], (case_id, rid)
            assert body["outcomes"][RULE_CODE[rid]] == exp["rule"], (case_id, rid)
        all_passed = all(e["rule"] == "PASSED" for e in ann["expected"]["requirements"].values())
        assert body["status"] == ("DECISION_READY" if all_passed else "RISK_DETECTED"), case_id
        if ann["expected"]["contains_prompt_injection"]:
            assert body["injection_flags"] >= 1, case_id
        seen.add(ann["scenario"])
    assert len(seen) == 8


def test_every_stored_fact_has_a_verified_span() -> None:
    with get_engine().begin() as conn:
        conn.execute(text("SELECT set_config('app.org_id', :o, true)"), {"o": DEMO_ORG_ID})
        rows = conn.execute(text(
            "SELECT f.quote, s.quoted, substring(d.content FROM s.char_start + 1 FOR s.char_end - s.char_start) AS src "
            "FROM clinical_facts f JOIN evidence_spans s ON s.id = f.evidence_span_id "
            "JOIN clinical_documents d ON d.id = s.document_id WHERE f.label IS NOT NULL")).all()
        unlinked = conn.execute(text(
            "SELECT count(*) FROM clinical_facts WHERE label IS NOT NULL AND evidence_span_id IS NULL")).scalar_one()
    assert rows
    assert unlinked == 0
    assert all(r.quote == r.quoted == r.src for r in rows)


def test_twin_shows_analysis_facts_and_cdi(client, login) -> None:  # type: ignore[no-untyped-def]
    h = login("sara.auth")
    partial = next(c for c, a in ANNOTATIONS.items() if a["scenario"] == "partial_duration")
    twin = client.get(f"/api/cases/{_ids(client, h)[partial]}", headers=h).json()
    assert twin["analyzed"] is True
    assert twin["analysis"]["mode"] == "baseline"
    assert twin["analysis"]["policyVersion"] == "DPA-LUMBAR-POL@2026.1"
    assert all(f["docRef"] and f["quote"] for f in twin["clinicalFacts"])
    ev = twin["evidenceItems"][0]
    assert ev["status"] == "PARTIAL"
    assert ev["cdiQuestion"] and ev["cdiQuestionAr"]
    assert {a["agentId"] for a in twin["agentRuns"]} >= {"A1", "A2", "A3", "A5"}
    assert any(e["action"].startswith("Analysis (baseline)") for e in twin["auditTrail"])


def test_rerun_replaces_current_results_and_keeps_history(client, login) -> None:  # type: ignore[no-untyped-def]
    h = login("sara.auth")
    cid = _ids(client, h)["SYN-MRI-001"]
    before = len(client.get(f"/api/cases/{cid}", headers=h).json()["clinicalFacts"])
    assert _analyze(client, cid, h).status_code == 200
    after = client.get(f"/api/cases/{cid}", headers=h).json()
    assert len(after["clinicalFacts"]) == before
    with get_owner_engine().begin() as conn:
        runs = conn.execute(text("SELECT count(*) FROM analysis_runs WHERE authorization_request_id = :c"),
                            {"c": cid}).scalar_one()
    assert runs == 2
    v = client.get(f"/api/audit/{cid}/verify", headers=login("noura.audit")).json()
    assert v["valid"] is True


def test_legacy_case_is_analysed_from_its_note(client, login) -> None:  # type: ignore[no-untyped-def]
    h = login("sara.auth")
    ids = _ids(client, h)
    r = _analyze(client, ids["AUTH-2026-4922"], h)
    assert r.status_code == 200, r.text
    twin = client.get(f"/api/cases/{ids['AUTH-2026-4922']}", headers=h).json()
    assert all(f["docRef"] == "AUTH-2026-4922-NOTE" for f in twin["clinicalFacts"])


def test_analyze_errors_and_permissions(client, login) -> None:  # type: ignore[no-untyped-def]
    h = login("sara.auth")
    ids = _ids(client, h)
    assert _analyze(client, ids["AUTH-2026-8103"], h).status_code == 409  # DENIED
    assert _analyze(client, ids["SYN-MRI-010"], login("dr.khalid")).status_code == 403
    assert _analyze(client, ids["SYN-MRI-010"], login("other.auth")).status_code == 404
    assert _analyze(client, "not-a-uuid", h).status_code == 404
    assert _analyze(client, ids["SYN-MRI-010"], login("omar.coder")).status_code == 200


def test_streaming_progress(client, login) -> None:  # type: ignore[no-untyped-def]
    h = login("sara.auth")
    cid = _ids(client, h)["SYN-MRI-011"]
    limiter._hits.clear()
    with client.stream("POST", f"/api/cases/{cid}/analyze", params={"stream": "true", "mode": "baseline"},
                       headers=h) as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        raw = "".join(r.iter_text())
    events = [line.split(": ", 1)[1] for line in raw.splitlines() if line.startswith("event: ")]
    assert events[0] == "start"
    assert events[-1] == "done"
    assert events.count("step") == 8  # RUNNING + COMPLETED for A1, A2, A3, A5
