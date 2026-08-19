"""OAuth state store with consume-once semantics.

The GitHub OAuth ``state`` must be verifiable from any API replica, so the
secret is stored in Redis (``SET EX`` / ``GETDEL``) with an in-process fallback
for single-process degradation. A popped entry can never be consumed twice.
"""

from __future__ import annotations

import logging
import secrets
import time
from collections import OrderedDict

from .cache import client as _cache_client

logger = logging.getLogger("projectdna.state_store")

_MEM_MAX_ENTRIES = 10_000
_mem: OrderedDict[str, tuple[str, float]] = OrderedDict()


def remember(key: str, ttl_seconds: int) -> str:
    value = secrets.token_urlsafe(16)
    c = _cache_client()
    if c is not None:
        try:
            c.set(f"oauth:state:{key}", value, ex=ttl_seconds)
            return value
        except Exception:  # noqa: BLE001
            pass
    _mem[key] = (value, time.monotonic())
    _mem.move_to_end(key)
    while len(_mem) > _MEM_MAX_ENTRIES:
        _mem.popitem(last=False)
    return value


def consume(key: str, ttl_seconds: int) -> str | None:
    """Return the stored secret once, or None if absent/expired/already used."""
    c = _cache_client()
    if c is not None:
        try:
            return c.getdel(f"oauth:state:{key}")
        except Exception:  # noqa: BLE001
            pass
    entry = _mem.pop(key, None)
    if not entry:
        return None
    value, ts = entry
    if time.monotonic() - ts > ttl_seconds:
        return None
    return value