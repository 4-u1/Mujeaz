"""The committed dataset must match the generator, and every annotated span must be exact."""

import base64
import json
from pathlib import Path

from evals.generator.generate import OUT, SCENARIOS, generate


def test_committed_dataset_matches_generator() -> None:
    files = generate()
    for name, content in files.items():
        assert (OUT / name).read_text(encoding="utf-8") == content, name


def test_scenario_mix() -> None:
    manifest = json.loads((OUT / "manifest.json").read_text())
    assert manifest["cases"] == 50
    assert manifest["scenarios"] == dict(SCENARIOS)


def test_every_span_is_verbatim() -> None:
    docs = {}
    for path in Path(OUT).glob("SYN-*.json"):
        for e in json.loads(path.read_text())["entry"]:
            r = e["resource"]
            if r["resourceType"] == "DocumentReference":
                docs[r["id"]] = base64.b64decode(r["content"][0]["attachment"]["data"]).decode()
    anns = [json.loads(line) for line in (OUT / "annotations.jsonl").read_text().splitlines()]
    assert len(anns) == 50
    for a in anns:
        assert a["facts"], a["case_id"]
        for s in a["facts"]:
            assert docs[s["doc_ref"]][s["start"]:s["end"]] == s["quoted"]


def test_ground_truth_is_consistent() -> None:
    for line in (OUT / "annotations.jsonl").read_text().splitlines():
        a = json.loads(line)
        r1 = a["expected"]["requirements"]["R1_conservative_therapy_6w"]
        if a["scenario"] == "red_flag":
            assert r1["rule"] == "PASSED" and a["expected"]["red_flag_exemption"]
        if r1["evidence"] == "FOUND":
            assert any(f["label"] == "conservative_therapy" for f in a["facts"])
        if a["scenario"] == "injection":
            assert any(f["label"] == "injection_text" for f in a["facts"])
