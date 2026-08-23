"""Standardized exceptions for Project DNA adapters and application layer.

All adapter-level exceptions should subclass one of these, and FastAPI exception
handlers should catch the base classes to produce consistent error envelopes.

Also provides the fire-and-forget error notification helper used by the
exception handlers below.
"""

from __future__ import annotations

import logging
import urllib.parse
import urllib.request
from typing import Optional

from ..config import settings

logger = logging.getLogger("projectdna.errors")


class DNAError(Exception):
    """Base class for all Project DNA application errors.

    ``status_code`` lets the FastAPI layer translate domain failures into the
    right HTTP status without importing HTTP concerns here."""

    def __init__(
        self,
        message: str,
        code: str = "DNA_ERROR",
        retryable: bool = False,
        status_code: int = 400,
    ):
        self.message = message
        self.code = code
        self.retryable = retryable
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(DNAError):
    """Resource not found (HTTP 404)."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message=message, code="NOT_FOUND", retryable=False, status_code=404)


class ValidationError(DNAError):
    """Input validation failure (HTTP 422)."""

    def __init__(self, message: str = "Validation error", code: str = "VALIDATION_ERROR"):
        super().__init__(message=message, code=code, retryable=False, status_code=422)


class ConflictError(DNAError):
    """State conflict, e.g. duplicate resource (HTTP 409)."""

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message=message, code="CONFLICT", retryable=False, status_code=409)


class PermissionDeniedError(DNAError):
    """Authenticated but not allowed (HTTP 403)."""

    def __init__(self, message: str = "Not allowed"):
        super().__init__(message=message, code="FORBIDDEN", retryable=False, status_code=403)


class AuthError(DNAError):
    """Authentication/authorization failure (HTTP 401)."""

    def __init__(self, message: str = "Not authenticated", code: str = "UNAUTHORIZED"):
        super().__init__(message=message, code=code, retryable=False, status_code=401)


class RateLimitedError(DNAError):
    """Rate limit exceeded, indicates retry after delay."""

    def __init__(self, retry_after: str | None = None, message: str = "Rate limited"):
        self.retry_after = retry_after
        super().__init__(message=message, code="RATE_LIMITED", retryable=True)


class DatabaseError(DNAError):
    """Database operation failure."""

    def __init__(self, message: str = "Database error", retryable: bool = True):
        super().__init__(message=message, code="DB_ERROR", retryable=retryable)


class InsufficientCoverageError(DNAError):
    """DNA score withheld due to insufficient coverage."""

    def __init__(self, message: str = "Insufficient coverage for score"):
        super().__init__(message=message, code="INSUFFICIENT_COVERAGE", retryable=False)


class AnalysisError(DNAError):
    """Analysis pipeline failure."""

    def __init__(self, message: str = "Analysis failed", code: str = "ANALYSIS_FAILED", retryable: bool = True):
        super().__init__(message=message, code=code, retryable=retryable)


def notify(
    title: str,
    message: str,
    level: str = "error",
    metadata: Optional[dict] = None,
) -> None:
    """Fire-and-forget error notification.

    Sends a minimal payload in a daemon thread so the request path never blocks.
    If ``error_webhook_url`` is not configured the notify function is a no-op.
    """
    url = settings.error_webhook_url
    if not url:
        return
    data = urllib.parse.urlencode({"title": title, "message": message, "level": level, "metadata": str(metadata or {})}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=5) as _:
            logger.info("error webhook delivered %s", url)
    except Exception:  # noqa: BLE001
        logger.warning("error webhook FAILED %s", url)