"""FastAPI application factory."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.ai.router import router as ai_router
from app.auth_router import router as auth_router
from app.cases.router import router as cases_router
from app.cdi.router import router as cdi_router
from app.config import get_settings
from app.db import get_engine
from app.observability import RequestContextMiddleware, configure_logging, request_id_var
from app.orchestrator.router import router as analysis_router

log = logging.getLogger("mujeaz")


def _error(status: int, code: str, message: str, details: Any = None) -> JSONResponse:
    body: dict[str, Any] = {"error": {"code": code, "message": message, "request_id": request_id_var.get()}}
    if details is not None:
        body["error"]["details"] = details
    # `detail` kept for clients written against FastAPI defaults.
    body["detail"] = message
    return JSONResponse(status_code=status, content=body)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(
        title="Mujeaz API",
        version=__version__,
        description="Prior-authorization readiness and revenue assurance. Synthetic data only; NPHIES is simulated.",
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        resp = _error(exc.status_code, f"http_{exc.status_code}", str(exc.detail))
        for k, v in (exc.headers or {}).items():
            resp.headers[k] = v
        return resp

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"loc": list(e.get("loc", [])), "msg": e.get("msg")} for e in exc.errors()]
        return _error(422, "validation_error", "Request validation failed", details)

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error", exc_info=exc)
        return _error(500, "internal_error", "Internal server error")

    @app.get("/healthz", tags=["ops"])
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "mujeaz-api", "version": __version__}

    @app.get("/readyz", tags=["ops"])
    def readyz() -> JSONResponse:
        try:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001
            return _error(503, "not_ready", "Database unavailable")
        return JSONResponse({"status": "ready"})

    app.include_router(auth_router)
    app.include_router(cases_router)
    app.include_router(ai_router)
    app.include_router(analysis_router)
    app.include_router(cdi_router)
    return app


app = create_app()
