"""Revocable server-side sessions with Redis and in-memory fallback.

Redis-backed:
  - Sessions stored as ``sessions:{sid}`` = user_id with an EXPIRE (TTL).
  - Per-user index ``sessions:user:{user_id}`` = set of sids for revoke_all.

In-memory fallback (single-process degradation, same pattern as
``adapters/state_store``):
  - ``_mem_sid_to_user`` : OrderedDict[sid, (user_id, expiry_ts)].
  - ``_mem_user_to_sids``  : dict[user_id, set[sid]].
"""

from __future__ import annotations

import logging
import secrets
import time
from collections import OrderedDict
from typing import Optional

from ..config import settings
from .cache import client as _cache_client

logger = logging.getLogger("projectdna.sessions")

# ── In-memory fallback ────────────────────────────────────────────────────

_MEM_MAX_ENTRIES = 5_000
_mem_sid_to_user: OrderedDict[str, tuple[str, float]] = OrderedDict()
_mem_user_to_sids: dict[str, set[str]] = {}


def _mem_evict() -> None:
    """Pop oldest entries until we are under the max."""
    while len(_mem_sid_to_user) > _MEM_MAX_ENTRIES:
        _mem_sid_to_user.popitem(last=False)


# ── Public API ────────────────────────────────────────────────────────────

def create(user_id: str) -> str:
    """Create a new session for *user_id* and return the session ID (sid).

    In production the sid is stored in Redis with a TTL equal to
    ``settings.session_ttl_seconds``.  When Redis is unavailable the
    in-memory fallback is used.
    """
    sid = secrets.token_urlsafe(32)
    ttl = settings.session_ttl_seconds
    c = _cache_client()
    if c is not None:
        try:
            pipe = c.pipeline()
            pipe.set(f"sessions:{sid}", user_id, ex=ttl)
            pipe.sadd(f"sessions:user:{user_id}", sid)
            pipe.execute()
            logger.info("session created sid=%s user=%s ttl=%d", sid[:8], user_id, ttl)
            return sid
        except Exception:  # noqa: BLE001
            pass

    # In-memory fallback
    _mem_sid_to_user[sid] = (user_id, time.monotonic() + ttl)
    _mem_user_to_sids.setdefault(user_id, set()).add(sid)
    _mem_evict()
    return sid


def resolve(sid: str) -> Optional[str]:
    """Return the user_id for *sid* if the session is still valid, else None.

    The session is considered expired when its TTL has elapsed.
    """
    c = _cache_client()
    if c is not None:
        try:
            user_id = c.get(f"sessions:{sid}")
            if user_id is not None:
                return user_id
        except Exception:  # noqa: BLE001
            pass

    # In-memory fallback
    entry = _mem_sid_to_user.pop(sid, None)
    if entry is None:
        return None
    user_id, expiry_ts = entry
    if time.monotonic() > expiry_ts:
        _mem_user_to_sids.get(user_id, set()).discard(sid)
        return None
    return user_id


def revoke(sid: str) -> bool:
    """Revoke (invalidate) the session *sid*.  Returns ``True`` if the
    session existed and was removed."""
    c = _cache_client()
    if c is not None:
        try:
            # Fetch user_id *before* deleting the forward entry.
            user_id = c.get(f"sessions:{sid}")
            if user_id is None:
                return False
            pipe = c.pipeline()
            pipe.delete(f"sessions:{sid}")
            pipe.srem(f"sessions:user:{user_id}", sid)
            pipe.execute()
            return True
        except Exception:  # noqa: BLE001
            pass

    # In-memory fallback
    entry = _mem_sid_to_user.pop(sid, None)
    if entry is None:
        return False
    user_id, _ = entry
    _mem_user_to_sids.get(user_id, set()).discard(sid)
    return True


def revoke_all(user_id: str) -> int:
    """Revoke every session belonging to *user_id* (e.g. on password change
    or forced logout everywhere).  Returns the number of sessions revoked."""
    c = _cache_client()
    revoked = 0
    if c is not None:
        try:
            sids = c.smembers(f"sessions:user:{user_id}")
            if sids:
                pipe = c.pipeline()
                for s in sids:
                    pipe.delete(f"sessions:{s}")
                    pipe.srem(f"sessions:user:{user_id}", s)
                results = pipe.execute()
                revoked = sum(1 for r in results if r)
        except Exception:  # noqa: BLE001
            pass

    # In-memory fallback
    sids = _mem_user_to_sids.pop(user_id, set())
    for s in sids:
        _mem_sid_to_user.pop(s, None)
    _mem_user_to_sids.pop(user_id, None)
    return revoked


def cleanup_expired() -> int:
    """Remove any in-memory sessions whose TTL has elapsed.

    Call periodically from a background task or as part of startup.
    Returns the number of sessions cleaned."""
    revoked = 0
    now = time.monotonic()
    to_delete: list[str] = []
    for sid, (_, expiry_ts) in _mem_sid_to_user.items():
        if now > expiry_ts:
            to_delete.append(sid)
    for sid in to_delete:
        user_id, _ = _mem_sid_to_user.pop(sid, (None, None))
        _mem_user_to_sids.get(user_id, set()).discard(sid)
        revoked += 1
    return revoked