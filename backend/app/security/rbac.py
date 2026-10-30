"""Role → permission matrix (ADR 0003). Every endpoint declares the permission it needs."""

from enum import StrEnum


class Role(StrEnum):
    PHYSICIAN = "physician"
    AUTH_OFFICER = "auth_officer"
    CODER = "coder"
    APPEALS_OFFICER = "appeals_officer"
    RCM_MANAGER = "rcm_manager"
    AUDITOR = "auditor"


class Permission(StrEnum):
    CASE_READ = "case:read"
    CASE_ANALYZE = "case:analyze"
    CASE_DOCUMENT = "case:document"
    CASE_APPROVE_SUBMISSION = "case:approve_submission"
    PAYER_RECORD_RESPONSE = "payer:record_response"
    APPEAL_DRAFT = "appeal:draft"
    APPEAL_APPROVE = "appeal:approve"
    AUDIT_READ = "audit:read"
    METRICS_READ = "metrics:read"


ROLE_DESCRIPTIONS: dict[Role, str] = {
    Role.PHYSICIAN: "Writes orders; answers documentation queries",
    Role.AUTH_OFFICER: "Prepares, reviews and submits prior-authorization requests",
    Role.CODER: "Reviews diagnosis and service coding",
    Role.APPEALS_OFFICER: "Drafts and submits appeals for denied requests",
    Role.RCM_MANAGER: "Oversees revenue-cycle performance; approves appeals",
    Role.AUDITOR: "Read-only access to cases and the audit trail",
}

P = Permission
MATRIX: dict[Role, frozenset[Permission]] = {
    Role.PHYSICIAN: frozenset({P.CASE_READ, P.CASE_DOCUMENT}),
    Role.AUTH_OFFICER: frozenset(
        {P.CASE_READ, P.CASE_ANALYZE, P.CASE_APPROVE_SUBMISSION, P.PAYER_RECORD_RESPONSE, P.AUDIT_READ,
         P.METRICS_READ}
    ),
    Role.CODER: frozenset({P.CASE_READ, P.CASE_ANALYZE}),
    Role.APPEALS_OFFICER: frozenset({P.CASE_READ, P.APPEAL_DRAFT, P.APPEAL_APPROVE}),
    Role.RCM_MANAGER: frozenset({P.CASE_READ, P.APPEAL_APPROVE, P.AUDIT_READ, P.METRICS_READ}),
    Role.AUDITOR: frozenset({P.CASE_READ, P.AUDIT_READ, P.METRICS_READ}),
}


def permissions_for(roles: list[str]) -> frozenset[Permission]:
    granted: set[Permission] = set()
    for name in roles:
        try:
            granted |= MATRIX[Role(name)]
        except ValueError:
            continue  # unknown roles grant nothing
    return frozenset(granted)


def has_permission(roles: list[str], permission: Permission) -> bool:
    return permission in permissions_for(roles)
