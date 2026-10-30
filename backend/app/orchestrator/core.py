"""Analysis pipeline (pure): A1 → verify → injection flags → A2 → A3 → A5.

No database access here, so the same code runs in the API and in the eval runner.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.agents import a1_baseline, a1_llm, a2_evidence, a5_readiness, injection
from app.agents.types import EvidenceResult, Fact, InjectionFlag, Mode, PatientRecord, RuleResult
from app.llm.provider import Provider
from app.rules import engine

Emit = Callable[[str, dict[str, Any]], None]


@dataclass
class StepRecord:
    agent_id: str
    name: str
    name_ar: str
    status: str
    summary: str
    summary_ar: str
    latency_ms: int
    output: dict[str, Any] = field(default_factory=dict)
    model: str = "baseline-rules"
    prompt_version: str = "n/a"


@dataclass
class AnalysisResult:
    mode: Mode
    facts: list[Fact]
    injection_flags: list[InjectionFlag]
    evidence: dict[str, EvidenceResult]
    rules: list[RuleResult]
    readiness: a5_readiness.Readiness
    steps: list[StepRecord]
    rejected_quotes: list[str]
    policy_version: str
    fallback_reason: str | None = None

    @property
    def decision_ready(self) -> bool:
        return self.readiness.overall >= 90 and all(r.outcome != "FAILED" for r in self.rules)


class NoPolicy(Exception):
    pass


def _noop(_: str, __: dict[str, Any]) -> None:
    return None


def analyze(record: PatientRecord, *, mode: Mode = "baseline", provider: Provider | None = None,
            price_sar: float = 0, emit: Emit = _noop) -> AnalysisResult:
    policy = engine.policy_for(record.payer_code, record.service_code)
    if policy is None:
        raise NoPolicy(f"no policy for payer {record.payer_code} and service {record.service_code}")
    steps: list[StepRecord] = []
    rejected: list[str] = []
    fallback: str | None = None

    emit("step", {"agent": "A1", "status": "RUNNING"})
    t0 = time.perf_counter()
    model, prompt_version = "baseline-rules", "n/a"
    if mode == "llm" and provider is not None:
        try:
            run = a1_llm.extract(record.documents, provider)
            facts, rejected = run.facts, run.rejected
            model = run.usage[0].model if run.usage else provider.name
            prompt_version = run.prompt_version
        except Exception as exc:  # noqa: BLE001 — provider failure falls back to the baseline, labelled
            fallback = f"LLM unavailable ({type(exc).__name__}); baseline used"
            mode = "baseline"
            facts = a1_baseline.extract(record.documents)
    else:
        mode = "baseline"
        facts = a1_baseline.extract(record.documents)
    ms = int((time.perf_counter() - t0) * 1000)
    steps.append(StepRecord("A1", "Clinical Understanding Agent", "وكيل الفهم السريري", "COMPLETED",
                            f"{len(facts)} verified facts from {len(record.documents)} documents"
                            + (f"; {len(rejected)} unsupported quotes rejected" if rejected else ""),
                            f"{len(facts)} حقيقة موثقة من {len(record.documents)} مستند"
                            + (f"؛ رُفض {len(rejected)} اقتباس غير موجود" if rejected else ""),
                            ms, {"facts": len(facts), "rejected": len(rejected)}, model, prompt_version))
    emit("step", {"agent": "A1", "status": "COMPLETED", "facts": len(facts)})

    flags = injection.detect(record.documents)

    emit("step", {"agent": "A2", "status": "RUNNING"})
    t0 = time.perf_counter()
    evidence = {rid: a2_evidence.evaluate_requirement(rid, spec, facts, record.documents)
                for rid, spec in policy.requirements.items()}
    r1 = next(iter(evidence.values()))
    steps.append(StepRecord("A2", "Evidence Hunter Agent", "وكيل صيد الأدلة السريرية",
                            "COMPLETED" if r1.status == "FOUND" else "FLAGGED",
                            f"{r1.status}: {r1.reason}", f"{r1.status}: {r1.reason_ar}",
                            int((time.perf_counter() - t0) * 1000),
                            {rid: e.status for rid, e in evidence.items()}))
    emit("step", {"agent": "A2", "status": "COMPLETED", "evidence": {k: v.status for k, v in evidence.items()}})

    emit("step", {"agent": "A3", "status": "RUNNING"})
    t0 = time.perf_counter()
    rules = engine.evaluate(policy, facts=facts, evidence=evidence, diagnosis_code=record.diagnosis_code)
    failed = [r for r in rules if r.outcome != "PASSED"]
    steps.append(StepRecord("A3", "Policy Reasoning Agent", "وكيل مطابقة السياسات",
                            "FLAGGED" if failed else "COMPLETED",
                            f"{len(rules) - len(failed)}/{len(rules)} rules passed ({policy.code}@{policy.version})",
                            f"{len(rules) - len(failed)}/{len(rules)} قواعد مستوفاة ({policy.code}@{policy.version})",
                            int((time.perf_counter() - t0) * 1000),
                            {r.code: r.outcome for r in rules}, "rules-engine", f"{policy.code}@{policy.version}"))
    emit("step", {"agent": "A3", "status": "COMPLETED", "rules": {r.code: r.outcome for r in rules}})

    emit("step", {"agent": "A5", "status": "RUNNING"})
    exempt = any(r.outcome == "PASSED" and r.reason.startswith("Exempt") for r in rules)
    readiness = a5_readiness.assess(record, facts, evidence, rules, price_sar, exempt)
    steps.append(StepRecord("A5", "Revenue Risk Agent", "وكيل مخاطر الإيرادات", "COMPLETED",
                            f"Readiness {readiness.overall}/100; denial risk {readiness.denial_risk}%",
                            f"الجاهزية {readiness.overall}/100؛ مخاطر الرفض {readiness.denial_risk}%", 0,
                            {"overall": readiness.overall, "gate": readiness.gate}, "deterministic-v1", "PRD §8"))
    emit("step", {"agent": "A5", "status": "COMPLETED", "overall": readiness.overall})
    return AnalysisResult(mode, facts, flags, evidence, rules, readiness, steps, rejected,
                          f"{policy.code}@{policy.version}", fallback)
