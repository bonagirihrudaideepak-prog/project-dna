"""Centralized cache service with cache-aside pattern and consistent invalidation.

Provides a single point for cache operations across the application, ensuring
consistent key naming, metric tracking, and invalidation strategies.

All operations degrade gracefully when Redis is unavailable: reads return None,
writes/invalidations are no-ops. The underlying adapter reconnects on a short
backoff, so recovery from a Redis outage requires no restart.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

from ..config import settings
from . import metrics
from .cache import client as _cache_client

logger = logging.getLogger("projectdna.cache_service")

# Key namespaces invalidated together when a project mutates.
_PROJECT_LIST_PREFIX = "projects:list:"

# Per-key locks so a hot expiring key is computed once per process instead of
# by every concurrent request (stampede protection).
_locks_guard = threading.Lock()
_key_locks: dict[str, threading.Lock] = {}
_MAX_KEY_LOCKS = 5_000


def _key_lock(key: str) -> threading.Lock:
    with _locks_guard:
        lock = _key_locks.get(key)
        if lock is None:
            if len(_key_locks) >= _MAX_KEY_LOCKS:
                _key_locks.clear()  # crude bound; recomputed lazily afterwards
            lock = _key_locks.setdefault(key, threading.Lock())
        return lock


class CacheService:
    """Service-layer cache wrapper providing consistent access patterns."""

    def __init__(self):
        self._redis = None

    def _ensure_redis(self):
        """Return the Redis client or None. Retries until the adapter succeeds;
        the adapter itself applies connect backoff so this is cheap when down."""
        if self._redis is None:
            self._redis = _cache_client()
        return self._redis

    # ── Cache-aside helpers ────────────────────────────────────────────

    def get(self, key: str) -> Any | None:
        """Retrieve a value from cache. Returns None if miss or Redis down."""
        c = self._ensure_redis()
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

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in cache with optional TTL."""
        c = self._ensure_redis()
        if c is None:
            return
        try:
            c.set(key, json.dumps(value, default=str), ex=ttl or settings.cache_default_ttl)
        except Exception:  # noqa: BLE001
            pass

    def delete(self, key: str) -> None:
        """Delete a specific cache key."""
        c = self._ensure_redis()
        if c is None:
            return
        try:
            c.delete(key)
        except Exception:  # noqa: BLE001
            pass

    def delete_prefix(self, prefix: str) -> None:
        """Delete all keys matching a prefix."""
        c = self._ensure_redis()
        if c is None:
            return
        try:
            keys = list(c.scan_iter(match=f"{prefix}*", count=200))
            if keys:
                c.delete(*keys)
        except Exception:  # noqa: BLE001
            pass

    # ── Project-level invalidation ──────────────────────────────────────

    def invalidate_project(self, project_id: str) -> None:
        """Drop every cache key that could be stale after a project mutation."""
        c = self._ensure_redis()
        if c is None:
            logger.warning("Redis unavailable during project cache invalidation")
            return
        try:
            pipe = c.pipeline(transaction=False)
            pipe.delete(f"projects:item:{project_id}")
            pipe.delete(f"snapshots:list:{project_id}")
            pipe.execute()
            self.delete_prefix(_PROJECT_LIST_PREFIX)
            logger.info("cache invalidated for project %s", project_id)
        except Exception:  # noqa: BLE001
            logger.warning("cache invalidation failed for project %s", project_id)

    # ── Snapshot-level invalidation ─────────────────────────────────────

    def invalidate_snapshot(self, snapshot_id: str) -> None:
        """Drop cache keys associated with a specific snapshot."""
        c = self._ensure_redis()
        if c is None:
            logger.warning("Redis unavailable during snapshot cache invalidation")
            return
        try:
            pipe = c.pipeline(transaction=False)
            pipe.delete(f"dna:{snapshot_id}")
            pipe.delete(f"timeline:{snapshot_id}")
            pipe.execute()
            logger.info("cache invalidated for snapshot %s", snapshot_id)
        except Exception:  # noqa: BLE001
            logger.warning("cache invalidation failed for snapshot %s", snapshot_id)

    # ── Metrics-aware cache-aside ───────────────────────────────────────

    def get_or_compute(self, key: str, compute_fn, ttl: int | None = None) -> Any:
        """Cache-aside with metrics and per-key singleflight.

        On a miss, concurrent callers serialize on the key's lock; whoever
        enters second finds the freshly computed value in cache instead of
        re-running ``compute_fn``."""
        c = self._ensure_redis()
        if c is None:
            return compute_fn()

        try:
            raw = c.get(key)
            if raw is not None:
                metrics.cache_hits.inc()
                return json.loads(raw)
        except Exception:  # noqa: BLE001
            return compute_fn()

        metrics.cache_misses.inc()
        with _key_lock(key):
            try:
                raw = c.get(key)  # winner may have filled it while we waited
                if raw is not None:
                    metrics.cache_hits.inc()
                    return json.loads(raw)
                result = compute_fn()
                c.set(key, json.dumps(result, default=str), ex=ttl or settings.cache_default_ttl)
                return result
            except Exception:  # noqa: BLE001
                metrics.cache_misses.inc()
                return compute_fn()
