"""Authentication and GitHub connection routers."""

from __future__ import annotations

import secrets
import urllib.parse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ...adapters.db import get_db
from ...adapters.rate_limit import consume as rate_limit_consume
from ...adapters.security import create_session_token, encrypt_token
from ...adapters.sessions import revoke as session_revoke
from ...adapters.state_store import consume as state_consume
from ...adapters.state_store import remember as state_remember
from ...config import settings
from ...models import GitHubConnection, User
from ..deps import current_user
from ..schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

# OAuth state: stored in Redis (shared across API replicas) with a short TTL.
_STATE_TTL_SECONDS = 600

# Per-IP fixed-window limit on OAuth start requests, enforced across replicas.
_RATE_MAX = 20
_RATE_WINDOW_SECONDS = 60


def _session_cookie(request: Request, token: str) -> Response:
    secure = request.url.scheme == "https"
    resp = Response(status_code=302, headers={"Location": settings.app_base_url})
    resp.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=settings.session_ttl_seconds,
        path="/",
    )
    return resp


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/github/start")
def github_start(request: Request):
    if not rate_limit_consume(f"oauth:start:{_client_ip(request)}", _RATE_MAX, _RATE_WINDOW_SECONDS):
        raise HTTPException(status_code=429, detail="Too many requests; try again shortly")
    if not settings.github_client_id:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    state = secrets.token_urlsafe(32)
    state_remember(state, _STATE_TTL_SECONDS)
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "read:user repo",
        "state": state,
    }
    url = "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)
    return RedirectResponse(url, status_code=302)


@router.get("/github/callback")
async def github_callback(code: str, state: str, request: Request, db: Session = Depends(get_db)):
    if not state_consume(state, _STATE_TTL_SECONDS):
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
def me(user_id: str = Depends(current_user), db: Session = Depends(get_db)):
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
    sid = request.cookies.get("session")
    if sid:
        session_revoke(sid)
    resp = Response(status_code=200, content='{"ok": true}')
    resp.delete_cookie("session", path="/")
    return resp