"""A3 Policy Reasoning — deterministic rules engine over versioned YAML policies.

The model never decides a mandatory rule. Predicates are small, typed and tested.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.agents.types import EvidenceResult, Fact, RuleOutcome, RuleResult

POLICY_DIR = Path(__file__).resolve().parent / "policies"


@dataclass(frozen=True)
class Policy:
    code: str
    version: str
    payer: str
    service_codes: tuple[str, ...]
    raw: dict[str, Any]

    @property
    def rules(self) -> list[dict[str, Any]]:
        return list(self.raw["rules"])

    @property
    def requirements(self) -> dict[str, dict[str, Any]]:
        return dict(self.raw.get("requirements", {}))

    @property
    def decision_ready_min(self) -> int:
        return int(self.raw.get("decision", {}).get("ready_min", 90))

    @property
    def accepts_post_request_addenda(self) -> bool:
        return bool(self.raw.get("addenda", {}).get("accepts_post_request", False))


# --------------------------------------------------------------------------------- criteria
# A requirement's `satisfied_if` is a small tree: {min_weeks: n} | {min_sessions: n} |
# {any_of: [...]} | {all_of: [...]}. A fact satisfies it from its parsed `value` only.

def satisfies(criteria: dict[str, Any], value: dict[str, Any]) -> bool:
    if "any_of" in criteria:
        return any(satisfies(c, value) for c in criteria["any_of"])
    if "all_of" in criteria:
        return all(satisfies(c, value) for c in criteria["all_of"])
    if "min_weeks" in criteria:
        return float(value.get("weeks") or 0) >= float(criteria["min_weeks"])
    if "min_sessions" in criteria:
        return float(value.get("sessions") or 0) >= float(criteria["min_sessions"])
    raise ValueError(f"unknown criterion {criteria!r}")


def describe(criteria: dict[str, Any], ar: bool = False) -> str:
    if "any_of" in criteria:
        return (" أو " if ar else " or ").join(describe(c, ar) for c in criteria["any_of"])
    if "all_of" in criteria:
        return (" و" if ar else " and ").join(describe(c, ar) for c in criteria["all_of"])
    if "min_weeks" in criteria:
        n = f"{float(criteria['min_weeks']):g}"
        return f"{n} أسابيع على الأقل" if ar else f"at least {n} weeks"
    if "min_sessions" in criteria:
        n = f"{float(criteria['min_sessions']):g}"
        return f"{n} جلسات مكتملة على الأقل" if ar else f"at least {n} completed sessions"
    raise ValueError(f"unknown criterion {criteria!r}")


@lru_cache
def load_policies() -> tuple[Policy, ...]:
    out = []
    for path in sorted(POLICY_DIR.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        out.append(Policy(raw["policy"], str(raw["version"]), raw["payer"], tuple(raw["service_codes"]), raw))
    return tuple(out)


def policy_for(payer_code: str, service_code: str) -> Policy | None:
    for p in load_policies():
        if p.payer == payer_code and service_code in p.service_codes:
            return p
    return None


def evaluate(
    policy: Policy,
    *,
    facts: list[Fact],
    evidence: dict[str, EvidenceResult],
    diagnosis_code: str,
) -> list[RuleResult]:
    labels = {f.label for f in facts}
    results: list[RuleResult] = []
    for rule in policy.rules:
        outcome: RuleOutcome
        is_exempt = False
        pred = rule["predicate"]
        if pred == "evidence_status":
            exempt = [lab for lab in rule.get("exempt_if_any_fact", []) if lab in labels]
            ev = evidence.get(rule["requirement_id"])
            status = ev.status if ev else "MISSING"
            if exempt:
                is_exempt = True
                outcome = "PASSED"
                reason = f"Exempt: documented {', '.join(exempt)}."
                reason_ar = "مُستثنى: توجد مؤشرات خطيرة موثقة."
            else:
                outcome = rule["outcomes"][status]
                reason = f"Evidence {status}: {ev.reason}" if ev else "No evidence evaluated."
                reason_ar = f"الدليل {status}: {ev.reason_ar}" if ev else "لم يُقيَّم أي دليل."
        elif pred == "diagnosis_prefix_in":
            code = (diagnosis_code or "").upper()
            ok = any(code.startswith(p.upper()) for p in rule["prefixes"])
            outcome = "PASSED" if ok else "FAILED"
            reason = f"Diagnosis {code} {'is' if ok else 'is not'} compatible with the requested service."
            reason_ar = f"التشخيص {code} {'متوافق' if ok else 'غير متوافق'} مع الخدمة المطلوبة."
        else:
            raise ValueError(f"unknown predicate {pred!r} in {policy.code}")
        results.append(RuleResult(rule["code"], rule["id"], outcome, bool(rule.get("mandatory", True)),
                                  reason, reason_ar, policy.version, is_exempt))
    return results
