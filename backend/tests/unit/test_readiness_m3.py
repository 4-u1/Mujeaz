"""M3: criteria predicates, policy settings, readiness explanation, addendum exclusion."""

from dataclasses import replace
from datetime import date

import pytest

from app.agents.types import Document, PatientRecord
from app.orchestrator.core import analyze
from app.rules import engine
from app.rules.engine import describe, satisfies
from app.scoring.scoring import js_round


@pytest.mark.parametrize(("criteria", "value", "ok"), [
    ({"min_weeks": 6}, {"weeks": 6}, True),
    ({"min_weeks": 6}, {"weeks": 5.9}, False),
    ({"min_weeks": 6}, {}, False),
    ({"min_sessions": 6}, {"sessions": 6}, True),
    ({"any_of": [{"min_weeks": 8}, {"min_sessions": 6}]}, {"weeks": 4, "sessions": 6}, True),
    ({"any_of": [{"min_weeks": 8}, {"min_sessions": 6}]}, {"weeks": 7, "sessions": 5}, False),
    ({"all_of": [{"min_weeks": 6}, {"min_sessions": 6}]}, {"weeks": 6, "sessions": 5}, False),
    ({"all_of": [{"min_weeks": 6}, {"min_sessions": 6}]}, {"weeks": 6, "sessions": 6}, True),
])
def test_criteria(criteria: dict, value: dict, ok: bool) -> None:  # type: ignore[type-arg]
    assert satisfies(criteria, value) is ok


def test_describe_and_unknown_criterion() -> None:
    assert describe({"any_of": [{"min_weeks": 8}, {"min_sessions": 6}]}) == "at least 8 weeks or at least 6 completed sessions"
    assert "أسابيع" in describe({"min_weeks": 6}, ar=True)
    with pytest.raises(ValueError):
        satisfies({"max_weeks": 2}, {})


def test_policy_settings() -> None:
    p = engine.policy_for("DPA", "72148")
    assert p is not None
    assert p.decision_ready_min == 90
    assert p.accepts_post_request_addenda is True


def _rec(*docs: Document, dx: str = "M51.26", payer: str = "DPA") -> PatientRecord:
    return PatientRecord("T", docs, dx, "72148", payer, date(2026, 9, 1), docs[0].doc_ref)


INDEX = Document("D1", "orthopedic-note", "en", date(2026, 9, 1),
                 "Low back pain for 10 weeks. Straight leg raise positive. Plan: MRI lumbar spine without contrast.")
ADDENDUM = Document("D1-ADD", "addendum", "en", date(2026, 9, 2),
                    "Completed physiotherapy: 8 sessions over 6 weeks.")


@pytest.mark.parametrize("docs", [(INDEX,), (INDEX, ADDENDUM)])
def test_explanation_reproduces_score(docs: tuple[Document, ...]) -> None:
    res = analyze(_rec(*docs), price_sar=2800)
    ex = res.readiness.explanation
    assert js_round(sum(c["contribution"] for c in ex["components"])) == ex["weightedTotal"]
    assert ex["weightedTotal"] - ex["gateReduction"] == res.readiness.overall
    for c in ex["components"]:
        assert (c["score"] < 100) == bool(c["causes"])
        assert len(c["causes"]) == len(c["causesAr"])


def test_missing_therapy_is_explained() -> None:
    res = analyze(_rec(INDEX), price_sar=2800)
    ex = res.readiness.explanation
    assert res.readiness.overall == 51  # 0·0.30 + 50·0.25 + 100·0.15 + 100·0.15 + 30·0.10 + 100·0.05 = 50.5
    assert ex["gate"] is None and ex["gateReduction"] == 0  # already below the 60 cap
    ce = next(c for c in ex["components"] if c["component"] == "clinicalEvidence")
    assert ce["score"] == 0 and "MISSING" in ce["causes"][0]


def test_addendum_counts_only_when_the_payer_accepts_it(monkeypatch: pytest.MonkeyPatch) -> None:
    accepted = analyze(_rec(INDEX, ADDENDUM), price_sar=2800)
    assert accepted.evidence["R1_conservative_therapy_6w"].status == "FOUND"
    assert accepted.decision_ready

    p = engine.policy_for("DPA", "72148")
    assert p is not None
    strict = replace(p, raw={**p.raw, "addenda": {"accepts_post_request": False}})
    monkeypatch.setattr(engine, "policy_for", lambda *_: strict)
    refused = analyze(_rec(INDEX, ADDENDUM), price_sar=2800)
    ev = refused.evidence["R1_conservative_therapy_6w"]
    assert ev.status == "MISSING"
    assert "does not accept addenda" in ev.reason
    assert refused.excluded_addenda == ("D1-ADD",)
    assert any(f.doc_ref == "D1-ADD" for f in refused.facts)  # still shown to reviewers
    assert not refused.decision_ready


def test_decision_threshold_comes_from_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    p = engine.policy_for("DPA", "72148")
    assert p is not None
    strict = replace(p, raw={**p.raw, "decision": {"ready_min": 101}})
    monkeypatch.setattr(engine, "policy_for", lambda *_: strict)
    res = analyze(_rec(INDEX, ADDENDUM), price_sar=2800)
    assert res.readiness.overall == 100
    assert res.decision_ready is False


def test_wrong_coding_gate_is_explained() -> None:
    res = analyze(_rec(INDEX, ADDENDUM, dx="J45.909"), price_sar=2800)
    ex = res.readiness.explanation
    assert ex["gate"] == "INVALID_CODING"
    assert ex["gateReduction"] == ex["weightedTotal"] - 50
    assert ex["gateText"].startswith("Capped at 50")
    coding = next(c for c in ex["components"] if c["component"] == "codingIntegrity")
    assert "J45.909" in coding["causes"][0]


def test_second_policy_is_configuration_only() -> None:
    dpb = engine.policy_for("DPB", "72148")
    assert dpb is not None and dpb.code == "DPB-LUMBAR-POL"
    assert dpb.accepts_post_request_addenda is False
    pt = Document("D2", "physiotherapy-note", "en", date(2026, 8, 20), "Physiotherapy record: 7 sessions completed over 4 weeks.")
    dpa_res = analyze(_rec(INDEX, pt), price_sar=2800)
    dpb_res = analyze(_rec(INDEX, pt, payer="DPB"), price_sar=2800)
    assert dpa_res.evidence["R1_conservative_therapy_6w"].status == "PARTIAL"  # 4 weeks < 6
    assert dpb_res.evidence["R1_conservative_therapy_dpb"].status == "FOUND"   # 7 sessions >= 6
    assert dpb_res.policy_version == "DPB-LUMBAR-POL@2026.1"


def test_payer_comes_from_the_bundle_coverage() -> None:
    import json
    from pathlib import Path

    from app.agents.fhir import payer_from_bundle, record_from_bundle

    root = Path(__file__).resolve().parents[3] / "evals" / "data"
    dpb = json.loads((root / "mri_lumbar_dpb" / "DPB-MRI-001.json").read_text(encoding="utf-8"))
    dev = json.loads((root / "mri_lumbar" / "SYN-MRI-001.json").read_text(encoding="utf-8"))
    assert payer_from_bundle(dpb) == "DPB" and record_from_bundle(dpb).payer_code == "DPB"
    assert payer_from_bundle(dev) == "DPA"
