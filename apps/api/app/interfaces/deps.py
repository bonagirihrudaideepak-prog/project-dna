"""Shared FastAPI dependencies."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, Request

from ..adapters.security import decode_session_token
from ..config import settings


def parse_id(value: str, field: str = "id") -> str:
    """Validate that a path/query id is a well-formed UUID.

    Rejects garbage before it reaches the DB instead of relying on a 404 from a
    string-vs-uuid column mismatch."""
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=422, detail=f"Invalid {field}")
    return str(parsed)


async def current_user(request: Request):
    """Resolve the authenticated user id from the HttpOnly session cookie.

    Cookie-only (never query params) so tokens cannot leak into logs or history."""
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = decode_session_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    request.state.user_id = user_id
    return user_id


async def optional_user(request: Request) -> str | None:
    """Like current_user but returns None when not authenticated.

    Used for fixture mode in development: projects seeded as fixtures are
    readable without a session. In production this enforces auth."""
    if settings.env == "production":
        return await current_user(request)
    token = request.cookies.get("session")
    if not token:
        request.state.user_id = None
        return None
    user_id = decode_session_token(token)
    request.state.user_id = user_id
    return user_id