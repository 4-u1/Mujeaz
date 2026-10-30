"""Demo Payer B split: 20 MRI Lumbar Spine cases for a second policy (M3).

DPB requires 8 weeks of conservative therapy OR 6 completed sessions, and does not accept
post-request addenda. Scenarios are chosen where DPA and DPB disagree, so a policy mix-up
fails the gates. Phrasing comes from a third template family.

    python -m evals.generator.dpb          # writes evals/data/mri_lumbar_dpb/
    python -m evals.generator.dpb --check
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from evals.generator.generate import DX_OK, DX_OK_ALT, DX_WRONG, SERVICE, NoteBuilder, _ref

SEED = 20261031
OUT = Path(__file__).resolve().parents[1] / "data" / "mri_lumbar_dpb"
BASE_DATE = date(2026, 9, 20)
PAYER = "DPB"
R1 = "R1_conservative_therapy_dpb"

# scenario: (cases, sessions range, weeks range, expected R1 evidence, expected R1 rule)
SCENARIOS: dict[str, tuple[int, tuple[int, int], tuple[int, int], str, str]] = {
    "found_weeks": (5, (4, 5), (8, 12), "FOUND", "PASSED"),       # weeks satisfy, sessions do not
    "found_sessions": (3, (6, 9), (4, 6), "FOUND", "PASSED"),     # sessions satisfy; DPA would say PARTIAL
    "short_both": (4, (3, 5), (6, 7), "PARTIAL", "WARNING"),      # DPA would say FOUND
    "missing": (3, (0, 0), (0, 0), "MISSING", "FAILED"),
    "contradictory": (2, (0, 0), (0, 0), "MISSING", "FAILED"),
    "red_flag": (2, (0, 0), (0, 0), "MISSING", "PASSED"),
    "wrong_coding": (1, (6, 8), (8, 10), "FOUND", "PASSED"),
}


def build(i: int, scenario: str, rng: random.Random) -> tuple[dict, dict]:
    cid, pid = f"DPB-MRI-{i:03d}", f"DPB-P-{3000 + i}"
    lang = rng.choice(["en", "ar", "en"])
    req_on = BASE_DATE + timedelta(days=rng.randint(0, 30))
    _, (s_lo, s_hi), (w_lo, w_hi), ev, rule = SCENARIOS[scenario]
    sessions, weeks = rng.randint(s_lo, s_hi), rng.randint(w_lo, w_hi)
    pain_weeks = max(weeks + 2, rng.randint(9, 16))
    dx = DX_WRONG if scenario == "wrong_coding" else rng.choice([DX_OK, DX_OK_ALT])

    idx = NoteBuilder(f"{cid}-D1")
    if lang == "en":
        idx.add("Orthopaedic consultation. ")
        idx.add(f"Lumbar pain with radiation to the leg for {pain_weeks} weeks", "symptom_duration")
        idx.add(". ")
        idx.add("Straight leg raise positive on the affected side", "exam_slr")
        idx.add(". ")
        if scenario == "contradictory":
            idx.add("Patient reports having finished a course of physiotherapy", "claimed_therapy")
            idx.add(". ")
        if scenario == "red_flag":
            idx.add("Saddle anaesthesia and new urinary retention noted", "red_flag")
            idx.add(". ")
        if scenario == "missing":
            idx.add("No physiotherapy has been tried so far", "therapy_negated")
            idx.add(". ")
        idx.add("Plan: MRI of the lumbar spine without contrast.", "requested_service")
    else:
        idx.add("استشارة عظام. ")
        idx.add(f"ألم قطني ممتد إلى الساق منذ {pain_weeks} أسابيع", "symptom_duration")
        idx.add(". ")
        idx.add("اختبار رفع الساق المستقيمة إيجابي في الجهة المصابة", "exam_slr")
        idx.add(". ")
        if scenario == "contradictory":
            idx.add("يذكر المريض أنه أنهى برنامج العلاج الطبيعي", "claimed_therapy")
            idx.add(". ")
        if scenario == "red_flag":
            idx.add("خدر سرجي مع احتباس بولي جديد", "red_flag")
            idx.add(". ")
        if scenario == "missing":
            idx.add("لم يخضع المريض لأي علاج طبيعي حتى الآن", "therapy_negated")
            idx.add(". ")
        idx.add("الخطة: رنين مغناطيسي للفقرات القطنية بدون صبغة.", "requested_service")

    docs = [(idx, f"{cid}-E1", req_on, "orthopedic-note", lang)]
    if sessions or scenario == "contradictory":
        pt = NoteBuilder(f"{cid}-D2")
        pl = rng.choice(["en", "ar"])
        if scenario == "contradictory":
            pt.add("Patient did not attend any of the booked physiotherapy sessions" if pl == "en"
                   else "لم يحضر المريض أيًا من جلسات العلاج الطبيعي المحجوزة", "therapy_not_attended")
            pt.add(".")
        elif pl == "en":
            pt.add(f"Physiotherapy record: {sessions} sessions completed over {weeks} weeks", "conservative_therapy")
            pt.add(". ")
            pt.add("Symptoms persist despite therapy", "persistent_symptoms")
            pt.add(".")
        else:
            pt.add(f"سجل العلاج الطبيعي: أكمل {sessions} جلسات خلال {weeks} أسابيع", "conservative_therapy")
            pt.add(". ")
            pt.add("الأعراض مستمرة رغم العلاج", "persistent_symptoms")
            pt.add(".")
        docs.append((pt, f"{cid}-E2", req_on - timedelta(days=7), "physiotherapy-note", pl))

    resources: list[dict] = [{"resourceType": "Patient", "id": pid, "gender": rng.choice(["male", "female"]),
                              "birthDate": f"{req_on.year - rng.randint(25, 70)}-01-01",
                              "name": [{"text": f"DPB Patient {i:03d} (synthetic)"}]},
                             {"resourceType": "Coverage", "id": f"{cid}-COV", "status": "active",
                              "beneficiary": _ref("Patient", pid),
                              "payor": [{"identifier": {"system": "urn:mujeaz:demo:payer", "value": PAYER}}]}]
    for nb, enc, when, dtype, dl in docs:
        text = nb.text()
        resources.append({"resourceType": "Encounter", "id": enc, "status": "finished", "type": [{"text": dtype}],
                          "subject": _ref("Patient", pid), "period": {"start": when.isoformat(), "end": when.isoformat()}})
        resources.append({"resourceType": "DocumentReference", "id": nb.doc_ref, "status": "current",
                          "type": {"text": dtype}, "subject": _ref("Patient", pid), "date": f"{when.isoformat()}T09:00:00Z",
                          "context": {"encounter": [_ref("Encounter", enc)]},
                          "content": [{"attachment": {"contentType": "text/plain; charset=utf-8", "language": dl,
                                                      "data": base64.b64encode(text.encode()).decode()}}]})
    resources.append({"resourceType": "Condition", "id": f"{cid}-C1",
                      "code": {"coding": [{"system": "urn:mujeaz:demo:diagnosis-code", "code": dx[0], "display": dx[1]}]},
                      "subject": _ref("Patient", pid), "encounter": _ref("Encounter", f"{cid}-E1")})
    resources.append({"resourceType": "ServiceRequest", "id": f"{cid}-SR1", "status": "active", "intent": "order",
                      "code": {"coding": [{"system": "urn:mujeaz:demo:procedure-code", "code": SERVICE[0]}]},
                      "subject": _ref("Patient", pid), "encounter": _ref("Encounter", f"{cid}-E1"),
                      "authoredOn": req_on.isoformat()})
    bundle = {"resourceType": "Bundle", "id": cid, "type": "collection",
              "meta": {"tag": [{"system": "urn:mujeaz:data", "code": "synthetic-dpb"}]},
              "entry": [{"fullUrl": f"urn:uuid:{r['resourceType']}-{r['id']}", "resource": r} for r in resources]}
    ann = {"case_id": cid, "scenario": scenario, "language": lang, "payer": PAYER, "requested_on": req_on.isoformat(),
           "service_code": SERVICE[0], "diagnosis_code": dx[0], "index_document": idx.doc_ref,
           "facts": [s.__dict__ for nb, *_ in docs for s in nb.spans],
           "expected": {"requirements": {
               R1: {"evidence": ev, "rule": rule},
               "R2_diagnosis_procedure_compatibility": {"rule": "FAILED" if scenario == "wrong_coding" else "PASSED"}},
               "red_flag_exemption": scenario == "red_flag", "contains_prompt_injection": False,
               "contradiction": scenario == "contradictory", "explicit_negation": scenario == "missing"}}
    return bundle, ann


def generate() -> dict[str, str]:
    rng = random.Random(SEED)
    plan = [s for s, spec in SCENARIOS.items() for _ in range(spec[0])]
    rng.shuffle(plan)
    files: dict[str, str] = {}
    anns = []
    for i, scenario in enumerate(plan, start=1):
        b, a = build(i, scenario, rng)
        files[f"{b['id']}.json"] = json.dumps(b, ensure_ascii=False, indent=1) + "\n"
        anns.append(a)
    files["annotations.jsonl"] = "".join(json.dumps(a, ensure_ascii=False) + "\n" for a in anns)
    counts = {s: sum(a["scenario"] == s for a in anns) for s in SCENARIOS}
    files["manifest.json"] = json.dumps({
        "dataset": "mri_lumbar_dpb", "split": "dpb", "version": 1, "seed": SEED, "payer": PAYER,
        "cases": len(anns), "scenarios": counts, "synthetic": True,
        "note": "Second payer policy (8 weeks or 6 sessions; no post-request addenda).",
        "sha256": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in sorted(files.items())},
    }, ensure_ascii=False, indent=1) + "\n"
    return files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    files = generate()
    if ap.parse_args().check:
        bad = [n for n, c in files.items() if not (OUT / n).exists() or (OUT / n).read_text(encoding="utf-8") != c]
        if bad:
            print(f"DPB dataset out of date: {bad[:5]}", file=sys.stderr)
            return 1
        print(f"DPB dataset OK ({len(files)} files)")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (OUT / name).write_text(content, encoding="utf-8")
    print(f"wrote {len(files)} files to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
