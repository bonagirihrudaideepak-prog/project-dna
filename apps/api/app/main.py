"""FastAPI application entrypoint for Project DNA."""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .adapters import metrics
from .adapters.cache import ping as cache_ping
from .adapters.db import engine, init_db
from .adapters.errors import DNAError, RateLimitedError
from .adapters.errors import notify as error_notify
from .adapters.logging_utils import log_with_context, new_request_id, setup_logging
from .config import settings
from .interfaces.api import alerts as alerts_api
from .interfaces.api import analysis as analysis_api
from .interfaces.api import archaeology as archaeology_api
from .interfaces.api import auth as auth_api
from .interfaces.api import dna as dna_api
from .interfaces.api import projects as projects_api

logger = logging.getLogger("projectdna.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("startup", extra={"extra_fields": {"env": settings.env}})
    try:
        init_db()
    except Exception as exc:  # noqa: BLE001
        logger.error("startup_db_init_failed", extra={"extra_fields": {"error": str(exc)[:300]}})
    yield


app = FastAPI(title="Project DNA", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = new_request_id()
    request.state.user_id = None
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 1)
    response.headers["X-Request-ID"] = request.state.request_id
    # Label by route template (e.g. /api/v1/projects/{project_id}), never the
    # raw path: raw paths embed UUIDs and would grow metric labels unboundedly.
    route = request.scope.get("route")
    path_label = getattr(route, "path", None) or "unmatched"
    labels = {"method": request.method, "path": path_label, "status": str(response.status_code)}
    metrics.http_requests.inc(labels)
    metrics.http_duration.observe(duration_ms / 1000.0, {"method": request.method, "path": path_label})
    log_with_context(
        logger,
        logging.INFO,
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration_ms,
        request_id=request.state.request_id,
        user_id=request.state.user_id,
    )
    return response


def _error_response(status: int, code: str, message: str, retryable: bool = False) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "retryable": retryable}},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """Consistent error envelope for DB failures."""
    from sqlalchemy.exc import IntegrityError

    log_with_context(
        logger, logging.ERROR, "db_error",
        request_id=getattr(request.state, "request_id", None),
        error=str(exc)[:500],
    )
    error_notify(
        title="Database error",
        message=str(exc)[:1000],
        level="error",
        metadata={"path": request.url.path, "method": request.method},
    )
    if isinstance(exc, IntegrityError):
        return _error_response(409, "CONFLICT", "Resource already exists or violates a constraint")
    return _error_response(500, "DB_ERROR", "Database error", retryable=True)


@app.exception_handler(DNAError)
async def dna_error_handler(request: Request, exc: DNAError):
    """Consistent error envelope for DNA application errors."""
    log_with_context(
        logger, logging.ERROR, "dna_error",
        request_id=getattr(request.state, "request_id", None),
        error=exc.message,
    )
    error_notify(
        title=exc.code,
        message=exc.message,
        level="error",
        metadata={"path": request.url.path, "method": request.method, "retryable": exc.retryable},
    )
    return _error_response(exc.status_code, exc.code, exc.message, retryable=exc.retryable)


_HTTP_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    503: "SERVICE_UNAVAILABLE",
}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Route HTTPException through the standard error envelope so every API
    error shares the ``{"error": {code, message, retryable}}`` contract."""
    log_with_context(
        logger, logging.INFO, "http_error",
        request_id=getattr(request.state, "request_id", None),
        status=exc.status_code,
        error=str(exc.detail)[:500],
    )
    code = _HTTP_ERROR_CODES.get(exc.status_code, f"HTTP_{exc.status_code}")
    response = _error_response(exc.status_code, code, str(exc.detail), retryable=exc.status_code >= 500 or exc.status_code == 429)
    if exc.headers:
        for key, value in exc.headers.items():
            response.headers[key] = value
    return response


@app.exception_handler(RateLimitedError)
async def rate_limited_handler(request: Request, exc: RateLimitedError):
    """Handle rate-limited errors with Retry-After header."""
    log_with_context(
        logger, logging.WARNING, "rate_limited",
        request_id=getattr(request.state, "request_id", None),
        error=exc.message,
    )
    response = _error_response(429, "RATE_LIMITED", exc.message, retryable=True)
    response.headers["Retry-After"] = str(exc.retry_after) if exc.retry_after else "60"
    return response


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    """Fallback for any unhandled exceptions."""
    log_with_context(
        logger, logging.ERROR, "unhandled_error",
        request_id=getattr(request.state, "request_id", None),
        error=str(exc)[:500],
    )
    error_notify(
        title="Unhandled error",
        message=str(exc)[:1000],
        level="error",
        metadata={"path": request.url.path, "method": request.method},
    )
    return _error_response(500, "INTERNAL_ERROR", "Internal server error", retryable=True)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "project-dna", "version": "0.1.0"}


@app.get("/api/health/ready")
def readiness():
    """True readiness: verifies the DB and cache are reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except SQLAlchemyError:
        db_ok = False
    cache_ok = cache_ping()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unreachable",
        "cache": "ok" if cache_ok else "unavailable",
    }


@app.get("/metrics")
def metrics_endpoint():
    """Prometheus text exposition of in-process metrics."""
    return Response(content=metrics.render(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/api/methodology")
def methodology():
    return {
        "model_version": "dna-core-1.0",
        "dimensions": [
            {"key": "technical_complexity", "name": "Technical Complexity", "direction": "descriptive"},
            {"key": "maintainability", "name": "Maintainability", "direction": "higher_is_better"},
            {"key": "testing_maturity", "name": "Testing Maturity", "direction": "higher_is_better"},
            {"key": "documentation_quality", "name": "Documentation Quality", "direction": "higher_is_better"},
            {"key": "evolution_health", "name": "Evolution Health", "direction": "higher_is_better"},
            {"key": "delivery_readiness", "name": "Delivery Readiness", "direction": "higher_is_better"},
            {"key": "scalability_readiness", "name": "Scalability Readiness", "direction": "higher_is_better"},
            {"key": "technical_debt_risk", "name": "Technical Debt Risk", "direction": "lower_is_better"},
        ],
        "coverage_labels": [
            {"below": 0.35, "label": "insufficient"},
            {"below": 0.60, "label": "low"},
            {"below": 0.80, "label": "moderate"},
            {"below": 1.01, "label": "high"},
        ],
        "min_coverage_for_score": 0.35,
        "caveats": [
            "Scores are descriptive evidence-weighted signals, not quality verdicts.",
            "Technical Debt Risk is 'lower is better'.",
            "A dimension with inadequate coverage is withheld, never scored as zero.",
            "Testing Maturity is not a claim about actual test coverage.",
            "LLM output is evidence-grounded and never used for scoring.",
        ],
    }


@app.get("/api/fixtures")
def fixtures():
    root = Path(settings.fixture_root)
    out = []
    if root.exists():
        for d in sorted(root.iterdir()):
            manifest = d / "manifest.json"
            if manifest.exists():
                try:
                    out.append(json.loads(manifest.read_text()))
                except Exception:
                    continue
    return out


app.include_router(auth_api.router, prefix="/api/v1")
app.include_router(projects_api.router, prefix="/api/v1")
app.include_router(dna_api.router, prefix="/api/v1")
app.include_router(alerts_api.router, prefix="/api/v1")
app.include_router(archaeology_api.router, prefix="/api/v1")
app.include_router(analysis_api.router, prefix="/api/v1")