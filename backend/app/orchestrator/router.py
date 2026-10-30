"""POST /api/cases/{id}/analyze — runs A1 → A2 → A3 → A5 and persists the result.

`?stream=true` returns Server-Sent Events (one `step` event per agent, then `done` or `error`).
The browser reads them with fetch streaming so the bearer token stays in the Authorization header.
"""

import json
import queue
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import Connection

from app.ai.router import limiter
from app.config import get_settings
from app.db import bind_org, get_engine
from app.orchestrator.service import CaseNotFound, NoPolicy, NotAnalyzable, run_analysis
from app.security.deps import CurrentUser, require
from app.security.rbac import Permission

router = APIRouter(prefix="/api", tags=["analysis"])


@contextmanager
def _tx(org_id: str) -> Iterator[Connection]:
    """One transaction per analysis; any exception rolls everything back."""
    with get_engine().begin() as conn:
        bind_org(conn, org_id)
        yield conn


def _case_id(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found") from exc


def _execute(conn: Connection, cid: str, user: CurrentUser, mode: Literal["baseline", "llm"] | None,
             emit: Any = None) -> dict[str, Any]:
    try:
        return run_analysis(conn, case_id=cid, org_id=user.org_id, actor=user.actor,
                            actor_label=user.name or user.username, mode=mode, emit=emit)
    except CaseNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found") from exc
    except NotAnalyzable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except NoPolicy as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"No payer policy is configured for this case ({exc})") from exc


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/cases/{case_id}/analyze", response_model=None)
def analyze_case(
    case_id: str,
    stream: bool = Query(default=False),
    mode: Literal["baseline", "llm"] | None = Query(default=None),
    user: CurrentUser = Depends(require(Permission.CASE_ANALYZE)),
) -> dict[str, Any] | StreamingResponse:
    cid = _case_id(case_id)
    limiter.check(f"analyze:{user.id}", get_settings().rate_limit_per_minute)
    if not stream:
        with _tx(user.org_id) as conn:
            return _execute(conn, cid, user, mode)

    events: queue.Queue[tuple[str, dict[str, Any]] | None] = queue.Queue()

    def worker() -> None:
        try:
            with _tx(user.org_id) as conn:
                result = _execute(conn, cid, user, mode, emit=lambda k, d: events.put((k, d)))
            events.put(("done", result))
        except HTTPException as exc:
            events.put(("error", {"status": exc.status_code, "message": exc.detail}))
        except Exception:  # noqa: BLE001 — reported to the client; the transaction is rolled back
            events.put(("error", {"status": 500, "message": "Analysis failed"}))
        finally:
            events.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def body() -> Iterator[str]:
        yield _sse("start", {"case_id": cid})
        while (item := events.get()) is not None:
            yield _sse(*item)

    return StreamingResponse(body(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
