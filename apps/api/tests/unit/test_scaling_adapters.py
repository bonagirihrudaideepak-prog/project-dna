"""Unit tests for the scaling adapters (cache, rate limit, state store, metrics).

Redis is deliberately not required: the fixtures force the graceful-degradation
path so tests stay deterministic and offline.
"""

import time
from types import SimpleNamespace

import pytest

from app.adapters import cache, metrics, rate_limit, state_store


@pytest.fixture(autouse=True)
def no_redis(monkeypatch):
    monkeypatch.setattr(cache, "settings", SimpleNamespace(redis_url="", cache_default_ttl=300))
    cache._client = None
    cache._next_attempt = 0.0
    rate_limit._mem.clear()
    state_store._mem.clear()
    yield


def test_cache_degrades_to_miss(no_redis):
    assert cache.client() is None
    assert cache.cache_get("x") is None
    cache.cache_set("x", {"a": 1})  # must not raise
    cache.cache_delete("x")
    cache.cache_delete_prefix("projects:list:")
    cache.invalidate_project("p1")
    assert cache.cache_get("x") is None


def test_rate_limit_in_memory_fallback(no_redis):
    for _ in range(3):
        assert rate_limit.consume("ip", 3, 60) is True
    assert rate_limit.consume("ip", 3, 60) is False


def test_rate_limit_window_expires(no_redis):
    rate_limit.consume("ip2", 1, 60)
    assert rate_limit.consume("ip2", 1, 60) is False
    rate_limit._mem["ip2"] = (time.monotonic() - 61, 1)
    assert rate_limit.consume("ip2", 1, 60) is True


def test_state_store_consume_once(no_redis):
    value = state_store.remember("st", 60)
    assert value
    assert state_store.consume("st", 60) == value
    assert state_store.consume("st", 60) is None


def test_state_store_expired(no_redis):
    state_store._mem["st2"] = ("secret", time.monotonic() - 61)
    assert state_store.consume("st2", 60) is None


def test_metrics_counter_render():
    metrics.http_requests.inc({"method": "GET", "path": "/x", "status": "200"})
    text = metrics.render()
    assert "# HELP http_requests_total" in text
    assert '# TYPE http_requests_total counter' in text
    assert 'http_requests_total{method="GET",path="/x",status="200"} 1' in text


def test_metrics_histogram_render():
    metrics.http_duration.observe(0.02, {"method": "GET", "path": "/x"})
    metrics.http_duration.observe(2.0, {"method": "GET", "path": "/x"})
    text = metrics.render()
    assert 'http_request_duration_seconds_bucket{le="0.05",method="GET",path="/x"} 1' in text
    assert 'http_request_duration_seconds_bucket{le="5",method="GET",path="/x"} 2' in text
    assert 'http_request_duration_seconds_bucket{le="+Inf",method="GET",path="/x"} 2' in text
    assert 'http_request_duration_seconds_sum{method="GET",path="/x"} 2.02' in text
    assert 'http_request_duration_seconds_count{method="GET",path="/x"} 2' in text


def test_metrics_gauge_render():
    metrics.queue_depth.set(4)
    text = metrics.render()
    assert 'queue_depth 4' in text