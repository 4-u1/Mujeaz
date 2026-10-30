"""Explicit case lifecycle (PRD §6). No transition happens outside this table."""

from dataclasses import dataclass
from enum import StrEnum

from app.security.rbac import Permission


class CaseStatus(StrEnum):
    DRAFT = "DRAFT"
    RISK_DETECTED = "RISK_DETECTED"
    EVIDENCE_SEARCHING = "EVIDENCE_SEARCHING"
    DECISION_READY = "DECISION_READY"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    RECOVERY_IN_PROGRESS = "RECOVERY_IN_PROGRESS"
    APPEAL_READY = "APPEAL_READY"
    RECOVERED = "RECOVERED"


@dataclass(frozen=True)
class Transition:
    permission: Permission
    human_gate: str | None = None  # recorded in human_reviews when set


S = CaseStatus
P = Permission
TRANSITIONS: dict[tuple[CaseStatus, CaseStatus], Transition] = {
    (S.DRAFT, S.RISK_DETECTED): Transition(P.CASE_ANALYZE),
    (S.DRAFT, S.DECISION_READY): Transition(P.CASE_ANALYZE),
    (S.RISK_DETECTED, S.EVIDENCE_SEARCHING): Transition(P.CASE_ANALYZE),
    (S.RISK_DETECTED, S.DECISION_READY): Transition(P.CASE_ANALYZE),
    (S.EVIDENCE_SEARCHING, S.DECISION_READY): Transition(P.CASE_ANALYZE),
    (S.EVIDENCE_SEARCHING, S.RISK_DETECTED): Transition(P.CASE_ANALYZE),
    (S.DECISION_READY, S.RISK_DETECTED): Transition(P.CASE_ANALYZE),
    (S.DECISION_READY, S.SUBMITTED): Transition(P.CASE_APPROVE_SUBMISSION, human_gate="SUBMISSION"),
    (S.SUBMITTED, S.APPROVED): Transition(P.PAYER_RECORD_RESPONSE),
    (S.SUBMITTED, S.DENIED): Transition(P.PAYER_RECORD_RESPONSE),
    (S.DENIED, S.RECOVERY_IN_PROGRESS): Transition(P.APPEAL_DRAFT),
    (S.RECOVERY_IN_PROGRESS, S.APPEAL_READY): Transition(P.APPEAL_DRAFT),
    (S.APPEAL_READY, S.RECOVERY_IN_PROGRESS): Transition(P.APPEAL_DRAFT),
    (S.APPEAL_READY, S.RECOVERED): Transition(P.APPEAL_APPROVE, human_gate="APPEAL"),
}

TERMINAL: frozenset[CaseStatus] = frozenset({S.APPROVED, S.RECOVERED})
RECOVERY_QUEUE: frozenset[CaseStatus] = frozenset({S.DENIED, S.RECOVERY_IN_PROGRESS, S.APPEAL_READY})


class IllegalTransition(Exception):
    pass


def get_transition(current: str, target: str) -> Transition:
    try:
        key = (CaseStatus(current), CaseStatus(target))
    except ValueError as exc:
        raise IllegalTransition(f"unknown status: {exc}") from exc
    t = TRANSITIONS.get(key)
    if t is None:
        raise IllegalTransition(f"{current} → {target} is not an allowed transition")
    return t


def allowed_targets(current: str) -> list[CaseStatus]:
    c = CaseStatus(current)
    return [to for (frm, to) in TRANSITIONS if frm == c]
