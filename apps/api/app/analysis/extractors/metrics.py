"""Computed repository metrics derived from inspected files and artifacts.

Every extractor returns a dict of raw values plus evidence IDs. These are the
"indicators" consumed by the scoring engine.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from ..inspector import InspectionResult


def module_depth(path: str) -> int:
    parts = [p for p in path.split("/") if p]
    return max(0, len(parts) - 1)


def compute_structural_breadth(result: InspectionResult) -> dict[str, Any]:
    source = [f for f in result.files if f.language and not f.is_generated and not f.category == "test"]
    dirs = {"/".join(f.path.split("/")[:-1]) for f in source if "/" in f.path}
    return {
        "raw_value": len(dirs),
        "dirs": len(dirs),
        "source_files": len(source),
        "evidence": [f"file:{f.path}" for f in source[:50]],
    }


def compute_dependency_breadth(result: InspectionResult) -> dict[str, Any]:
    manifests = [f for f in result.files if f.category == "manifest"]
    deps = 0
    detail = {}
    for m in manifests:
        if not m.content_preview:
            continue
        try:
            if m.path.endswith("package.json"):
                import json

                data = json.loads(m.content_preview)
                n = len(data.get("dependencies", {})) + len(data.get("devDependencies", {}))
                deps += n
                detail[m.path] = n
            elif m.path.endswith("pyproject.toml"):
                detail[m.path] = m.content_preview.count("\n") + 1
                deps += detail[m.path]
            elif m.path.endswith("requirements.txt"):
                n = sum(1 for line in m.content_preview.splitlines() if line and not line.startswith("#"))
                deps += n
                detail[m.path] = n
        except Exception:
            pass
    return {
        "raw_value": deps,
        "dependencies": deps,
        "manifest_count": len(manifests),
        "evidence": [f"file:{m.path}" for m in manifests],
        "detail": detail,
    }


def compute_integration_breadth(result: InspectionResult) -> dict[str, Any]:
    """Count distinct integration signals: databases, ORMs, caches, queues,
    external APIs, auth, storage, deployment targets."""
    signals = {"database": [], "api": [], "auth": [], "cache": [], "queue": [], "storage": [], "deploy": []}
    import re

    patterns = {
        "database": re.compile(r"(postgres|mysql|sqlite|mongo|redis|dynamo|cockroach|mariadb)", re.I),
        "api": re.compile(r"(grpc|graphql|restapi|fastapi|flask|express|django|spring|httpclient|openapi)", re.I),
        "auth": re.compile(r"(oauth|jwt|oidc|auth0|keycloak|passport|oidc|session)", re.I),
        "cache": re.compile(r"(memcached|redis|inmemorycache|lru_cache)", re.I),
        "queue": re.compile(r"(celery|rabbitmq|kafka|sqs|pubsub|bull|sidekiq)", re.I),
        "storage": re.compile(r"(s3|blob|storage|minio|gcs|gcsfuse)", re.I),
        "deploy": re.compile(r"(docker|kubernetes|helm|compose|terraform|pulumi|cloudformation|ecs|heroku|vercel|netlify)", re.I),
    }
    for f in result.files:
        if f.is_generated:
            continue
        blob = f.path
        if f.content_preview:
            blob = blob + "\n" + f.content_preview[:2000]
        for kind, pat in patterns.items():
            if pat.search(blob):
                signals[kind].append(f.path)
    count = sum(len(v) for v in signals.values())
    return {
        "raw_value": count,
        "signals": {k: len(v) for k, v in signals.items()},
        "evidence": [f"file:{p}" for paths in signals.values() for p in paths[:20]],
    }


def compute_heterogeneity(result: InspectionResult) -> dict[str, Any]:
    langs = result.languages
    config = [f for f in result.files if f.category == "config"]
    return {
        "raw_value": len(langs) + len(config),
        "languages": len(langs),
        "config_files": len(config),
        "evidence": [f"file:{f.path}" for f in config[:30]],
    }


def compute_file_size_health(result: InspectionResult) -> dict[str, Any]:
    source = [f for f in result.files if f.language and not f.is_generated]
    if not source:
        return {"raw_value": 1.0, "healthy": 0, "total": 0, "evidence": []}
    threshold = 400
    healthy = sum(1 for f in source if f.lines <= threshold)
    return {
        "raw_value": healthy / len(source),
        "healthy": healthy,
        "total": len(source),
        "threshold": threshold,
        "evidence": [f"file:{f.path}" for f in source if f.lines > threshold][:30],
    }


def compute_doc_quality(result: InspectionResult) -> dict[str, Any]:
    docs = [f for f in result.files if f.category == "docs"]
    readme_sections = 0
    for f in docs:
        if "readme" in f.path.lower():
            preview = f.content_preview or ""
            for section in ("install", "usage", "config", "getting started", "getting_started", "quick start", "run", "license", "api"):
                if section in preview.lower():
                    readme_sections += 1
    adrs = [f for f in docs if "adr" in f.path.lower() or "architecture" in f.path.lower() or "decision" in f.path.lower()]
    return {
        "raw_value": readme_sections,
        "readme_sections": readme_sections,
        "docs_files": len(docs),
        "adrs": len(adrs),
        "evidence": [f"file:{f.path}" for f in docs[:40]],
    }


def compute_test_signals(result: InspectionResult) -> dict[str, Any]:
    tests = [f for f in result.files if f.category == "test"]
    source = [f for f in result.files if f.language and not f.is_generated and f.category != "test"]
    ci_files = [f for f in result.files if f.category == "ci"]
    ci_text = "\n".join((f.content_preview or "") for f in ci_files)
    has_ci_test = any(k in ci_text.lower() for k in ("test", "pytest", "vitest", "jest", "go test", "mocha", "junit"))
    breadth = set()
    for f in tests:
        p = f.path.lower()
        if any(k in p for k in ("e2e", "endtoend", "end-to-end", "cypress", "playwright")):
            breadth.add("e2e")
        elif any(k in p for k in ("integration", "it_", "-it")):
            breadth.add("integration")
        else:
            breadth.add("unit")
    return {
        "test_files": len(tests),
        "source_files": len(source),
        "test_file_ratio": (len(tests) / len(source)) if source else 0.0,
        "has_ci_test": has_ci_test,
        "test_breadth": breadth,
        "evidence": [f"file:{f.path}" for f in tests[:40]] + [f"file:{f.path}" for f in ci_files[:10]],
    }


def compute_setup_signals(result: InspectionResult) -> dict[str, Any]:
    lockfiles = [f for f in result.files if f.extension == ".lock" or f.path.endswith(("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Pipfile.lock"))]
    env_files = [f for f in result.files if "env" in f.path.lower() and not f.path.lower().endswith(".md")]
    readme = [f for f in result.files if "readme" in f.path.lower()]
    return {
        "lockfiles": len(lockfiles),
        "env_templates": len(env_files),
        "readme_present": len(readme) > 0,
        "evidence": [f"file:{f.path}" for f in lockfiles + env_files[:10]],
    }


def compute_delivery_signals(result: InspectionResult) -> dict[str, Any]:
    ci = [f for f in result.files if f.category == "ci"]
    deploy = [f for f in result.files if f.category == "infra"]
    has_ci = len(ci) > 0
    ci_text = "\n".join((f.content_preview or "") for f in ci)
    checks = {"lint": "lint" in ci_text.lower(), "test": "test" in ci_text.lower(), "build": "build" in ci_text.lower()}
    env_sep = [f for f in result.files if "env" in f.path.lower() and not f.path.lower().endswith(".md")]
    return {
        "ci_files": len(ci),
        "has_ci": has_ci,
        "checks": checks,
        "deploy_files": len(deploy),
        "env_sep_files": len(env_sep),
        "evidence": [f"file:{f.path}" for f in ci + deploy[:20]],
    }


def compute_scalability_signals(result: InspectionResult) -> dict[str, Any]:
    async_files = [f for f in result.files if f.content_preview and any(
        k in (f.content_preview or "").lower() for k in ("async", "celery", "rabbitmq", "kafka", "queue", "redis", "cache")
    )]
    obs = [f for f in result.files if f.content_preview and any(
        k in (f.content_preview or "").lower() for k in ("healthz", "healthcheck", "prometheus", "logging", "structured log", "opentelemetry")
    )]
    migrations = [f for f in result.files if f.category == "migration"]
    concerns = set()
    for f in result.files:
        p = f.path.lower()
        if any(k in p for k in ("api/", "routes", "controllers", "handlers")):
            concerns.add("api")
        if "migration" in p or p.endswith(".sql"):
            concerns.add("data")
        if any(k in p for k in ("infra", "docker", "deploy", "k8s")):
            concerns.add("infra")
        if any(k in p for k in ("web", "frontend", "ui", "app/views", "pages", "components")):
            concerns.add("ui")
    return {
        "async_files": len(async_files),
        "obs_files": len(obs),
        "migrations": len(migrations),
        "concerns": len(concerns),
        "evidence": [f"file:{f.path}" for f in (async_files + obs + migrations)[:40]],
    }


def compute_debt_markers(result: InspectionResult) -> dict[str, Any]:
    total = 0
    files_with = 0
    for f in result.files:
        if f.content_preview:
            c = (f.content_preview or "").lower().count("todo") + (f.content_preview or "").lower().count("fixme")
            if c:
                files_with += 1
                total += c
    return {
        "raw_value": total,
        "markers": total,
        "files_with_markers": files_with,
        "evidence": [],
    }


def compute_churn_metrics(result: InspectionResult, file_changes: list[dict]) -> dict[str, Any]:
    """file_changes: list of dicts with file_path, additions, deletions."""
    by_file: dict[str, dict[str, int]] = {}
    for fc in file_changes:
        entry = by_file.setdefault(fc["file_path"], {"churn": 0, "changes": 0})
        entry["churn"] += fc.get("additions", 0) + fc.get("deletions", 0)
        entry["changes"] += 1
    if not by_file:
        return {
            "total_churn": 0,
            "hotspots": [],
            "concentration": 0.0,
            "avg_churn_per_file": 0.0,
            "evidence": [],
        }
    total_churn = sum(v["churn"] for v in by_file.values())
    ranked = sorted(by_file.items(), key=lambda kv: kv[1]["churn"], reverse=True)
    top_n = max(1, int(len(ranked) * 0.2))
    top_churn = sum(v["churn"] for _, v in ranked[:top_n])
    return {
        "total_churn": total_churn,
        "hotspots": [{"path": p, "churn": v["churn"], "changes": v["changes"]} for p, v in ranked[:10]],
        "concentration": (top_churn / total_churn) if total_churn else 0.0,
        "avg_churn_per_file": (total_churn / len(by_file)) if by_file else 0.0,
        "evidence": [f"file:{p}" for p, _ in ranked[:20]],
    }


def compute_change_coupling(file_changes: list[dict]) -> dict[str, Any]:
    """Co-change: how often files change together across a change unit."""
    from collections import defaultdict

    groups: dict[str, list[str]] = defaultdict(list)
    for fc in file_changes:
        groups[fc.get("change_unit", "all")].append(fc["file_path"])
    pairs: Counter = Counter()
    for paths in groups.values():
        unique = list(dict.fromkeys(paths))
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                pairs[tuple(sorted([unique[i], unique[j]]))] += 1
    if not pairs:
        return {"raw_value": 0.0, "max_coupling": 0.0, "avg_coupling": 0.0, "evidence": []}
    vals = list(pairs.values())
    return {
        "raw_value": max(vals),
        "max_coupling": max(vals),
        "avg_coupling": sum(vals) / len(vals),
        "evidence": [f"file:{a}~{b}" for (a, b) in pairs.most_common(10)],
    }
