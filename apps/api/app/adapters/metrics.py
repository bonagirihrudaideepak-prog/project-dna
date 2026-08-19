"""Minimal Prometheus text-format metrics registry (zero external deps).

Counters, gauges and histograms render in the standard exposition format so a
Prometheus scraper (or ``curl /metrics``) can consume them directly. Keeping it
dependency-free lets ``/metrics`` ship with the app instead of bolting on an
SDK; swap for ``prometheus-client`` later if richer features are needed.
"""

from __future__ import annotations

import threading

HISTOGRAM_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


class _Counter:
    __slots__ = ("name", "help", "label_names", "values", "lock")

    def __init__(self, name: str, help_: str, label_names: tuple[str, ...] = ()):
        self.name = name
        self.help = help_
        self.label_names = label_names
        self.values: dict[tuple[str, ...], float] = {}
        self.lock = threading.Lock()

    def inc(self, labels: dict[str, str] | None = None, amount: float = 1.0) -> None:
        key = tuple((labels or {}).get(n, "") for n in self.label_names)
        with self.lock:
            self.values[key] = self.values.get(key, 0.0) + amount

    def render(self, out: list[str]) -> None:
        out.append(f"# HELP {self.name} {self.help}")
        out.append(f"# TYPE {self.name} counter")
        for key, value in sorted(self.values.items()):
            label_str = self._labels(key)
            out.append(f"{self.name}{label_str} {value:.6g}")

    def _labels(self, key: tuple[str, ...]) -> str:
        if not self.label_names:
            return ""
        pairs = ",".join(f'{k}="{v}"' for k, v in zip(self.label_names, key))
        return "{" + pairs + "}"


class _Gauge:
    __slots__ = ("name", "help", "label_names", "values", "lock")

    def __init__(self, name: str, help_: str, label_names: tuple[str, ...] = ()):
        self.name = name
        self.help = help_
        self.label_names = label_names
        self.values: dict[tuple[str, ...], float] = {}
        self.lock = threading.Lock()

    def set(self, value: float, labels: dict[str, str] | None = None) -> None:
        key = tuple((labels or {}).get(n, "") for n in self.label_names)
        with self.lock:
            self.values[key] = float(value)

    def render(self, out: list[str]) -> None:
        out.append(f"# HELP {self.name} {self.help}")
        out.append(f"# TYPE {self.name} gauge")
        for key, value in sorted(self.values.items()):
            label_str = self._labels(key)
            out.append(f"{self.name}{label_str} {value:.6g}")

    def _labels(self, key: tuple[str, ...]) -> str:
        if not self.label_names:
            return ""
        pairs = ",".join(f'{k}="{v}"' for k, v in zip(self.label_names, key))
        return "{" + pairs + "}"


class _Histogram:
    __slots__ = ("name", "help", "label_names", "buckets", "values", "lock")

    def __init__(self, name: str, help_: str, label_names: tuple[str, ...] = ()):
        self.name = name
        self.help = help_
        self.label_names = label_names
        self.buckets = HISTOGRAM_BUCKETS
        self.values: dict[tuple[str, ...], dict] = {}
        self.lock = threading.Lock()

    def observe(self, value: float, labels: dict[str, str] | None = None) -> None:
        key = tuple((labels or {}).get(n, "") for n in self.label_names)
        with self.lock:
            entry = self.values.get(key)
            if entry is None:
                entry = {"buckets": {b: 0.0 for b in self.buckets}, "sum": 0.0, "count": 0}
                self.values[key] = entry
            entry["sum"] += value
            entry["count"] += 1
            for b in self.buckets:
                if value <= b:
                    entry["buckets"][b] += 1

    def render(self, out: list[str]) -> None:
        out.append(f"# HELP {self.name} {self.help}")
        out.append(f"# TYPE {self.name} histogram")
        for key, entry in sorted(self.values.items()):
            label_str = self._labels(key)
            for b in self.buckets:
                out.append(f'{self.name}_bucket{{le="{b:.6g}"{self._inline(key)}}} {entry["buckets"][b]:.6g}')
            count = entry["count"]
            out.append(f'{self.name}_bucket{{le="+Inf"{self._inline(key)}}} {count:.6g}')
            out.append(f"{self.name}_sum{label_str} {entry['sum']:.6g}")
            out.append(f"{self.name}_count{label_str} {count:.6g}")

    def _labels(self, key: tuple[str, ...]) -> str:
        if not self.label_names:
            return ""
        return "{" + ",".join(f'{k}="{v}"' for k, v in zip(self.label_names, key)) + "}"

    def _inline(self, key: tuple[str, ...]) -> str:
        if not self.label_names:
            return ""
        return "," + ",".join(f'{k}="{v}"' for k, v in zip(self.label_names, key))


class _Registry:
    def __init__(self) -> None:
        self._metrics: dict[str, object] = {}
        self._lock = threading.Lock()

    def counter(self, name: str, help_: str, label_names: tuple[str, ...] = ()) -> _Counter:
        return self._register(name, _Counter(name, help_, label_names))

    def gauge(self, name: str, help_: str, label_names: tuple[str, ...] = ()) -> _Gauge:
        return self._register(name, _Gauge(name, help_, label_names))

    def histogram(self, name: str, help_: str, label_names: tuple[str, ...] = ()) -> _Histogram:
        return self._register(name, _Histogram(name, help_, label_names))

    def _register(self, name: str, metric: object) -> object:
        with self._lock:
            existing = self._metrics.get(name)
            if existing is not None:
                return existing
            self._metrics[name] = metric
            return metric

    def render(self) -> str:
        with self._lock:
            names = sorted(self._metrics)
            snap = {n: self._metrics[n] for n in names}
        out: list[str] = []
        for name in names:
            snap[name].render(out)  # type: ignore[attr-defined]
        return "\n".join(out) + "\n"


registry = _Registry()

http_requests = registry.counter("http_requests_total", "HTTP requests processed", ("method", "path", "status"))
http_duration = registry.histogram("http_request_duration_seconds", "HTTP request latency", ("method", "path"))
cache_hits = registry.counter("cache_hits_total", "Cache reads served from cache")
cache_misses = registry.counter("cache_misses_total", "Cache reads that missed")
rate_limited = registry.counter("rate_limited_requests_total", "Requests rejected by the rate limiter")
jobs_completed = registry.counter("jobs_completed_total", "Analysis jobs completed")
jobs_failed = registry.counter("jobs_failed_total", "Analysis jobs failed")
queue_depth = registry.gauge("queue_depth", "Analysis jobs queued or retrying")
worker_online = registry.gauge("worker_online", "1 if at least one worker is running")


def render() -> str:
    return registry.render()