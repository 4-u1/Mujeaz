import pytest

from app.cases.state_machine import TRANSITIONS, CaseStatus, IllegalTransition, allowed_targets, get_transition
from app.security.rbac import MATRIX, Permission, Role, has_permission, permissions_for

EXPECTED = {
    Role.PHYSICIAN: {"case:read", "case:document"},
    Role.AUTH_OFFICER: {"case:read", "case:analyze", "case:approve_submission", "payer:record_response",
                        "audit:read", "metrics:read"},
    Role.CODER: {"case:read", "case:analyze"},
    Role.APPEALS_OFFICER: {"case:read", "appeal:draft", "appeal:approve"},
    Role.RCM_MANAGER: {"case:read", "appeal:approve", "audit:read", "metrics:read"},
    Role.AUDITOR: {"case:read", "audit:read", "metrics:read"},
}


@pytest.mark.parametrize("role", list(Role))
@pytest.mark.parametrize("perm", list(Permission))
def test_full_matrix(role: Role, perm: Permission) -> None:
    assert has_permission([role.value], perm) == (perm.value in EXPECTED[role])


def test_every_role_is_in_the_matrix() -> None:
    assert set(MATRIX) == set(Role)


def test_unknown_roles_grant_nothing() -> None:
    assert permissions_for(["superadmin", "root"]) == frozenset()


def test_only_auth_officer_can_approve_submission() -> None:
    holders = {r for r in Role if has_permission([r.value], Permission.CASE_APPROVE_SUBMISSION)}
    assert holders == {Role.AUTH_OFFICER}


def test_submission_and_appeal_are_human_gates() -> None:
    assert get_transition("DECISION_READY", "SUBMITTED").human_gate == "SUBMISSION"
    assert get_transition("APPEAL_READY", "RECOVERED").human_gate == "APPEAL"


@pytest.mark.parametrize("frm,to", [("DRAFT", "SUBMITTED"), ("APPROVED", "DENIED"), ("RECOVERED", "DRAFT"),
                                    ("DRAFT", "NOPE")])
def test_illegal_transitions(frm: str, to: str) -> None:
    with pytest.raises(IllegalTransition):
        get_transition(frm, to)


def test_terminal_states_have_no_exits() -> None:
    assert allowed_targets("APPROVED") == [] and allowed_targets("RECOVERED") == []


def test_every_state_is_reachable_from_draft() -> None:
    seen, frontier = {CaseStatus.DRAFT}, [CaseStatus.DRAFT]
    while frontier:
        cur = frontier.pop()
        for (f, t) in TRANSITIONS:
            if f == cur and t not in seen:
                seen.add(t)
                frontier.append(t)
    assert seen == set(CaseStatus)
