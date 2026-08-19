"""Centralized cache service with cache-aside pattern and consistent invalidation.

Provides a single point for cache operations across the application, ensuring
consistent key naming, metric tracking, and invalidation strategies.
"""

from __future__ import annotations

import logging
from typing import Any

from redis import Redis

from ..config import settings
from .cache import client as _cache_client

logger = logging.getLogger("projectdna.cache_service")


class CacheService:
    """Service-layer cache wrapper providing consistent access patterns."""

    def __init__(self):
        self._redis: Redis | None = None
        self._initialized: bool = False

    def _ensure_redis(self) -> Redis | None:
        """Lazily initialize Redis client, matching the adapter pattern."""
        if self._initialized:
            return self._redis
        self._redis = _cache_client()
        self._initialized = True
        return self._redis

    # ── Cache-aside helpers ────────────────────────────────────────────

    def get(self, key: str) -> Any | None:
        """Retrieve a value from cache. Returns None if miss or Redis down."""
        metrics = __import__("projectdna.adapters.metrics", fromlist=["metrics"])
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
            return __import__("json", fromlist=["json"]).loads(raw)
        except Exception:  # noqa: BLE001
            metrics.cache_misses.inc()
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in cache with optional TTL."""
        c = self._ensure_redis()
        if c is None:
            return
        try:
            c.set(key, __import__("json", fromlist=["json"]).dumps(value, default=str),
                  ex=ttl or settings.cache_default_ttl)
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
            # Still attempt in-memory cleanup patterns if needed
            logger.warning("Redis unavailable during project cache invalidation")
            return
        try:
            pipe = c.pipeline()
            pipe.delete(f"projects:item:{project_id}")
            pipe.delete(f"snapshots:list:{project_id}")
            pipe.delete_prefix("projects:list:")
            pipe.execute()
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
            pipe = c.pipeline()
            pipe.delete(f"dna:{snapshot_id}")
            pipe.delete(f"timeline:{snapshot_id}")
            pipe.execute()
            logger.info("cache invalidated for snapshot %s", snapshot_id)
        except Exception:  # noqa: BLE001
            logger.warning("cache invalidation failed for snapshot %s", snapshot_id)

    # ── Metrics-aware cache-aside ───────────────────────────────────────

    def get_or_compute(self, key: str, compute_fn, ttl: int | None = None) -> Any:
        """Cache-aside pattern with metrics: return cached if available, else compute."""
        metrics = __import__("projectdna.adapters.metrics", fromlist=["metrics"])
        c = self._ensure_redis()
        if c is None:
            # No cache available — compute and return directly
            result = compute_fn()
            return result

        try:
            raw = c.get(key)
            if raw is not None:
                metrics.cache_hits.inc()
                return __import__("json", fromlist=["json"]).loads(raw)

            metrics.cache_misses.inc()
            result = compute_fn()
            c.set(key, __import__("json", fromlist=["json"]).dumps(result, default=str),
                  ex=ttl or settings.cache_default_ttl)
            return result
        except Exception:  # noqa: BLE001
            metrics.cache_misses.inc()
            return compute_fn()