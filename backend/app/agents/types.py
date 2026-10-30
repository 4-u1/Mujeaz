"""Typed inputs and outputs shared by the agents (pure Python, no database)."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

EvidenceStatus = Literal["FOUND", "PARTIAL", "MISSING"]
RuleOutcome = Literal["PASSED", "WARNING", "FAILED"]
Mode = Literal["baseline", "llm"]

# Fact labels A1 can emit. `injection_text` is never a clinical fact; it is reported as a flag.
FACT_LABELS = (
    "symptom_duration",
    "exam_slr",
    "conservative_therapy",
    "medication",
    "persistent_symptoms",
    "red_flag",
    "claimed_therapy",
    "therapy_not_attended",
    "therapy_negated",
    "requested_service",
)


@dataclass(frozen=True)
class Document:
    doc_ref: str
    doc_type: str
    language: str
    authored_on: date | None
    text: str


@dataclass(frozen=True)
class PatientRecord:
    case_ref: str
    documents: tuple[Document, ...]
    diagnosis_code: str
    service_code: str
    payer_code: str
    requested_on: date | None
    index_doc_ref: str | None = None

    def doc(self, ref: str) -> Document:
        return next(d for d in self.documents if d.doc_ref == ref)


@dataclass(frozen=True)
class Fact:
    label: str
    doc_ref: str
    start: int
    end: int
    quote: str
    value: dict[str, Any] = field(default_factory=dict)
    fact_date: date | None = None
    confidence: int = 90
    source: Mode = "baseline"


@dataclass(frozen=True)
class InjectionFlag:
    doc_ref: str
    start: int
    end: int
    quote: str


@dataclass(frozen=True)
class EvidenceResult:
    requirement_id: str
    status: EvidenceStatus
    reason: str
    reason_ar: str
    facts: tuple[Fact, ...]
    retrieved: tuple[tuple[str, int, int, float], ...]  # (doc_ref, start, end, score) top-k chunks
    cdi_question: str | None = None
    cdi_question_ar: str | None = None


@dataclass(frozen=True)
class RuleResult:
    code: str
    rule_id: str
    outcome: RuleOutcome
    mandatory: bool
    reason: str
    reason_ar: str
    policy_version: str
    exempt: bool = False
