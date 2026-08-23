"""Distributed fixed-window rate limiter.

Uses a Redis counter (``INCR`` + ``EXPIRE`` on first hit) so limits hold across
API replicas. Falls back to an in-process window when Redis is unavailable, so a
Redis blip never turns into an open abuse hole on a single process.
"""

from __future__ import annotations

import logging
import time

from . import metrics
from .cache import client as _cache_client

logger = logging.getLogger("projectdna.rate_limit")

_mem: dict[str, tuple[float, int]] = {}


def consume(key: str, limit: int, window_seconds: int) -> bool:
    """Return True if a request from ``key`` is within ``limit``/``window``."""
    c = _cache_client()
    if c is not None:
        try:
            redis_key = f"rl:{key}"
            n = c.incr(redis_key)
            if n == 1:
                c.expire(redis_key, window_seconds)
            elif n > limit and c.ttl(redis_key) < 0:
                # Self-heal counters orphaned by a crash between INCR and
                # EXPIRE: without a TTL they would block the key forever.
                c.expire(redis_key, window_seconds)
            if n > limit:
                metrics.rate_limited.inc()
                return False
            return True
        except Exception:  # noqa: BLE001
            pass
    now = time.monotonic()
    start, count = _mem.get(key, (0.0, 0))
    if now - start > window_seconds:
        start, count = now, 0
    if count >= limit:
        metrics.rate_limited.inc()
        return False
    _mem[key] = (start, count + 1)
    return True