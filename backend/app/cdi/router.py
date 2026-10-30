"""Documentation queries (physician inbox), answers, and the what-if simulator."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import Connection

from app.ai.router import limiter
from app.cdi import service
from app.cdi.addendum import Answer
from app.config import get_settings
from app.db import bind_org, get_engine
from app.orchestrator.service import CaseNotFound, NoPolicy, NotAnalyzable
from app.security.deps import CurrentUser, require, tenant_conn
from app.security.rbac import Permission

router = APIRouter(prefix="/api", tags=["documentation"])


def _id(value: str, what: str) -> str:
    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{what} not found") from exc


@contextmanager
def _errors() -> Iterator[None]:
    try:
        yield
    except (CaseNotFound, service.QueryNotFound) as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found") from exc
    except (NotAnalyzable, service.QueryClosed) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except service.InvalidAnswer as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except NoPolicy as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"No payer policy for this case ({exc})") from exc


class AnswerIn(BaseModel):
    answer: Answer
    language: Literal["en", "ar"] = "en"


class DeclineIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


@router.get("/queries")
def list_queries(
    status_: Literal["OPEN", "ANSWERED", "DECLINED", "WITHDRAWN"] | None = Query(default="OPEN", alias="status"),
    case_id: str | None = Query(default=None),
    _: CurrentUser = Depends(require(Permission.CASE_READ)),
    conn: Connection = Depends(tenant_conn),
) -> dict[str, Any]:
    items = service.list_queries(conn, status=status_, case_id=_id(case_id, "Case") if case_id else None)
    return {"items": items, "total": len(items)}


@router.post("/queries/{query_id}/answer")
def answer(query_id: str, body: AnswerIn, user: CurrentUser = Depends(require(Permission.CASE_DOCUMENT)),
           conn: Connection = Depends(tenant_conn)) -> dict[str, Any]:
    qid = _id(query_id, "Query")
    limiter.check(f"cdi:{user.id}", get_settings().rate_limit_per_minute)
    with _errors():
        return service.answer_query(conn, query_id=qid, org_id=user.org_id, user_id=user.id, actor=user.actor,
                                    actor_label=user.name or user.username, answer=body.answer,
                                    language=body.language)


@router.post("/queries/{query_id}/decline")
def decline(query_id: str, body: DeclineIn, user: CurrentUser = Depends(require(Permission.CASE_DOCUMENT)),
            conn: Connection = Depends(tenant_conn)) -> dict[str, Any]:
    qid = _id(query_id, "Query")
    with _errors():
        return service.decline_query(conn, query_id=qid, org_id=user.org_id, actor=user.actor,
                                     actor_label=user.name or user.username, reason=body.reason)


@router.post("/cases/{case_id}/what-if")
def what_if(case_id: str, body: AnswerIn, user: CurrentUser = Depends(require(Permission.CASE_READ))) -> dict[str, Any]:
    """Simulation only: runs in a transaction that is always rolled back."""
    cid = _id(case_id, "Case")
    limiter.check(f"whatif:{user.id}", get_settings().rate_limit_per_minute * 3)
    with get_engine().connect() as conn, _errors():
        bind_org(conn, user.org_id)
        try:
            return service.simulate(conn, case_id=cid, org_id=user.org_id, answer=body.answer,
                                    language=body.language, author=user.name or user.username)
        finally:
            conn.rollback()
