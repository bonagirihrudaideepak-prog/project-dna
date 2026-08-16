"""Authentication and GitHub connection routers."""

from __future__ import annotations

import secrets
import time
import urllib.parse
from collections import OrderedDict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import GitHubConnection, User
from ..schemas import UserOut
from ..security import create_session_token, decrypt_token, encrypt_token

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory state store with a hard cap (prevents unbounded-memory DoS).
_STATE_MAX_ENTRIES = 10_000
_STATE_TTL_SECONDS = 600
_state_store: OrderedDict[str, tuple[str, float]] = OrderedDict()

# Simple per-IP token bucket for the OAuth start endpoint.
_RATE_MAX = 20
_RATE_WINDOW_SECONDS = 60
_rate_buckets: dict[str, tuple[float, int]] = {}


def _consume_rate(ip: str) -> bool:
    now = time.monotonic()
    window_start, count = _rate_buckets.get(ip, (0.0, 0))
    if now - window_start > _RATE_WINDOW_SECONDS:
        window_start, count = now, 0
    if count >= _RATE_MAX:
        return False
    _rate_buckets[ip] = (window_start, count + 1)
    return True


def _remember_state(state: str) -> None:
    _state_store[state] = (secrets.token_urlsafe(16), time.monotonic())
    _state_store.move_to_end(state)
    while len(_state_store) > _STATE_MAX_ENTRIES:
        _state_store.popitem(last=False)


def _consume_state(state: str) -> bool:
    entry = _state_store.pop(state, None)
    if not entry:
        return False
    _, ts = entry
    return time.monotonic() - ts <= _STATE_TTL_SECONDS


def _session_cookie(request: Request, token: str) -> Response:
    secure = request.url.scheme == "https"
    resp = Response(status_code=302, headers={"Location": settings.app_base_url})
    resp.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    return resp


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/github/start")
def github_start(request: Request):
    if not _consume_rate(_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests; try again shortly")
    if not settings.github_client_id:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    state = secrets.token_urlsafe(32)
    _remember_state(state)
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "read:user repo",
        "state": state,
    }
    url = "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)
    return {"authorization_url": url, "state": state}


@router.get("/github/callback")
async def github_callback(code: str, state: str, request: Request, db: Session = Depends(get_db)):
    if not _consume_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        token_data = resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="GitHub token exchange failed")

    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
    gh_user = user_resp.json()

    user = db.query(User).filter(User.github_user_id == gh_user["id"]).first()
    if not user:
        user = User(
            github_user_id=gh_user["id"],
            login=gh_user["login"],
            display_name=gh_user.get("name"),
            avatar_url=gh_user.get("avatar_url"),
        )
        db.add(user)
        db.flush()

    conn = db.query(GitHubConnection).filter(GitHubConnection.user_id == user.id).first()
    if conn:
        conn.encrypted_token = encrypt_token(access_token)
        conn.revoked_at = None
    else:
        db.add(GitHubConnection(
            user_id=user.id,
            encrypted_token=encrypt_token(access_token),
            scopes=token_data.get("scope", "").split(","),
        ))
    db.commit()

    session_token = create_session_token(str(user.id))
    return _session_cookie(request, session_token)


@router.get("/me", response_model=UserOut)
def me(request: Request, db: Session = Depends(get_db)):
    user_id = request.state.user_id
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    conn = db.query(GitHubConnection).filter(GitHubConnection.user_id == user.id, GitHubConnection.revoked_at.is_(None)).first()
    return UserOut(
        id=str(user.id),
        login=user.login,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        github_connected=conn is not None,
    )


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    resp = Response(status_code=200, content='{"ok": true}')
    resp.delete_cookie("session", path="/")
    return resp