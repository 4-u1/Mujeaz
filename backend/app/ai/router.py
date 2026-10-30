"""AI endpoints (same contract as the prototype, now authenticated and permission-checked)."""

import threading
import time
from collections import defaultdict, deque
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.ai.service import analyze_order, draft_appeal
from app.config import get_settings
from app.security.deps import CurrentUser, require
from app.security.rbac import Permission

router = APIRouter(prefix="/api/ai", tags=["ai"])


class _RateLimiter:
    """Sliding one-minute window per user. In-process; replace with Redis when scaled out."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= limit:
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Try again shortly.",
                                    headers={"Retry-After": str(int(60 - (now - q[0])) + 1)})
            q.append(now)


limiter = _RateLimiter()


class AnalyzeIn(BaseModel):
    clinicalNoteText: str = Field(min_length=1, max_length=20_000)
    payerName: str | None = Field(default=None, max_length=500)
    requestedService: str | None = Field(default=None, max_length=500)


@router.post("/analyze-order")
def analyze(body: AnalyzeIn, user: CurrentUser = Depends(require(Permission.CASE_ANALYZE))) -> dict[str, Any]:
    limiter.check(user.id, get_settings().rate_limit_per_minute)
    if not body.clinicalNoteText.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "clinicalNoteText is required")
    return analyze_order(body.clinicalNoteText, body.payerName, body.requestedService)


class EvidenceIn(BaseModel):
    fact: str = Field(max_length=1000)
    source: str = Field(max_length=300)
    date: str | None = Field(default=None, max_length=30)


class AppealIn(BaseModel):
    """Whitelisted fields only: no patient name or national ID reaches the model."""

    claimNumber: str | None = Field(default=None, max_length=500)
    payerName: str | None = Field(default=None, max_length=500)
    requestedService: str | None = Field(default=None, max_length=500)
    denialReason: str | None = Field(default=None, max_length=500)
    clinicalNoteText: str | None = Field(default=None, max_length=20_000)
    evidence: list[EvidenceIn] | None = Field(default=None, max_length=50)
    appealPackage: dict[str, Any] | None = None


@router.post("/generate-appeal")
def appeal(body: AppealIn, user: CurrentUser = Depends(require(Permission.APPEAL_DRAFT))) -> dict[str, Any]:
    limiter.check(user.id, get_settings().rate_limit_per_minute)
    return draft_appeal(body.model_dump())
