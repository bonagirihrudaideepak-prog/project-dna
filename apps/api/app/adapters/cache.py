"""Redis cache-aside layer with graceful degradation.

Every call is safe when Redis is down or misconfigured: misses return ``None``
and writes are no-ops, so the application keeps running at DB speed until Redis
recovers. Reconnect is attempted on a short backoff, never per-request.

Key namespace (single app, versioned for schema changes):

- ``projects:list:{user_key}:{page}:{per_page}``
- ``projects:item:{project_id}``
- ``snapshots:list:{project_id}``
- ``dna:{snapshot_id}``
- ``timeline:{snapshot_id}``
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from redis import Redis

from ..config import settings
from . import metrics

logger = logging.getLogger("projectdna.cache")

_client: Redis | None = None
_next_attempt: float = 0.0


def client() -> Redis | None:
    """Lazily-built Redis client with connect backoff. Never raises."""
    global _client, _next_attempt
    if _client is not None:
        return _client
    if time.monotonic() < _next_attempt:
        return None
    if not settings.redis_url:
        _next_attempt = time.monotonic() + 30
        return None
    try:
        c = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
            health_check_interval=30,
        )
        c.ping()
        _client = c
        logger.info("cache online: %s", settings.redis_url)
    except Exception as exc:  # noqa: BLE001
        _next_attempt = time.monotonic() + 5
        logger.warning("cache unavailable (%s), degrading to DB reads", exc)
        return None
    return _client


def ping() -> bool:
    c = client()
    if c is None:
        return False
    try:
        return bool(c.ping())
    except Exception:  # noqa: BLE001
        return False


def cache_get(key: str) -> Any | None:
    c = client()
    if c is None:
        metrics.cache_misses.inc()
        return None
    try:
        raw = c.get(key)
        if raw is None:
            metrics.cache_misses.inc()
            return None
        metrics.cache_hits.inc()
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        metrics.cache_misses.inc()
        return None


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    c = client()
    if c is None:
        return
    try:
        c.set(key, json.dumps(value, default=str), ex=ttl or settings.cache_default_ttl)
    except Exception:  # noqa: BLE001
        pass


def cache_delete(key: str) -> None:
    c = client()
    if c is None:
        return
    try:
        c.delete(key)
    except Exception:  # noqa: BLE001
        pass


def cache_delete_prefix(prefix: str) -> None:
    c = client()
    if c is None:
        return
    try:
        keys = list(c.scan_iter(match=f"{prefix}*", count=200))
        if keys:
            c.delete(*keys)
    except Exception:  # noqa: BLE001
        pass


def invalidate_project(project_id: str) -> None:
    """Drop every cache key that could be stale after a project mutation."""
    cache_delete(f"projects:item:{project_id}")
    cache_delete(f"snapshots:list:{project_id}")
    cache_delete_prefix("projects:list:")