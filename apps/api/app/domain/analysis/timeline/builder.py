"""Rule-based timeline reconstruction.

Combines exact events (releases, merged PRs, closed issues, tags), repository
changes (manifest changes, migrations), commit clusters, and user knowledge
(decisions, experiments) into a navigable chronology.
"""

from __future__ import annotations

from datetime import datetime, timedelta

CLUSTER_GAP_DAYS = 7
CLUSTER_COMPONENT_OVERLAP = 0.4

# Path heuristics for component detection (transparent, user-overridable)
PATH_RULES = [
    ("frontend", ["src/components", "src/pages", "src/app", "pages", "components", "frontend", "web/src", "src/ui", "views/"]),
    ("backend", ["api", "server", "routes", "controllers", "backend", "handlers", "services/"]),
    ("database", ["migrations", "schema", "alembic", "prisma", "db/", ".sql"]),
    ("tests", ["tests", "__tests__", "test_", "_test", ".test.", ".spec."]),
    ("infrastructure", ["docker", "deploy", "infra", "k8s", ".github", ".gitlab-ci", "terraform"]),
    ("documentation", ["docs", "README", "adr", "changelog"]),
    ("security", ["auth", "security", "oauth", "rbac", "middleware/auth"]),
]


def classify_component(path: str) -> str | None:
    for name, patterns in PATH_RULES:
        for p in patterns:
            if p in path:
                return name
    return None


def detect_component_overlap(paths_a: set[str], paths_b: set[str]) -> float:
    if not paths_a or not paths_b:
        return 0.0
    union = paths_a | paths_b
    inter = paths_a & paths_b
    return len(inter) / len(union)


def _component_set(file_paths: list[str]) -> set[str]:
    return {c for p in file_paths if (c := classify_component(p))}


def cluster_commits(commits: list[dict]) -> list[dict]:
    """Group commits into clusters by time gap and component overlap."""
    if not commits:
        return []
    ordered = sorted(commits, key=lambda c: c.get("occurred_at") or "")
    clusters: list[dict] = []
    current: list[dict] = []
    current_components: set[str] = set()

    def flush():
        nonlocal current, current_components
        if not current:
            return
        components = sorted(current_components)
        clusters.append(
            {
                "type": "commit_cluster",
                "title": _cluster_title(current),
                "occurred_at": current[0].get("occurred_at"),
                "end_at": current[-1].get("occurred_at"),
                "confidence": 0.9 if len(current) > 1 else 0.7,
                "provenance": "rule-derived",
                "commit_count": len(current),
                "commit_ids": [c["provider_id"] for c in current],
                "components": components,
                "source_urls": [c.get("source_url") for c in current if c.get("source_url")][:10],
                "paths": sorted({p for c in current for p in (c.get("metadata") or {}).get("paths", [])}),
            }
        )
        current = []
        current_components = set()

    prev_date = None
    for c in ordered:
        try:
            cur_date = datetime.fromisoformat((c.get("occurred_at") or "").replace("Z", "+00:00"))
        except (ValueError, TypeError):
            cur_date = None
        c_paths = set((c.get("metadata") or {}).get("paths", []))
        c_components = _component_set(list(c_paths))
        new_cluster = False
        if prev_date and cur_date:
            if (cur_date - prev_date) > timedelta(days=CLUSTER_GAP_DAYS):
                new_cluster = True
        if current and detect_component_overlap(current_components, c_components) < CLUSTER_COMPONENT_OVERLAP:
            new_cluster = True
        if new_cluster:
            flush()
        current.append(c)
        current_components |= c_components
        prev_date = cur_date
    flush()
    return clusters


def _cluster_title(commits: list[dict]) -> str:
    if not commits:
        return "Commit cluster"
    labels = [c.get("title") or "" for c in commits]
    longest = max(labels, key=len)
    if len(commits) == 1:
        return longest or "Commit"
    return f"{len(commits)} commits: {longest[:80]}" if longest else f"{len(commits)} commits"


def build_timeline_events(
    artifacts: list[dict],
    file_changes: list[dict],
    decisions: list[dict] | None = None,
    experiments: list[dict] | None = None,
) -> list[dict]:
    events: list[dict] = []
    seen: set[str] = set()

    def add(event: dict):
        key = f"{event.get('type')}:{event.get('occurred_at')}:{event.get('title')}"
        if key in seen:
            return
        seen.add(key)
        events.append(event)

    # Exact artifacts: releases, PRs, issues
    for a in artifacts:
        a_type = a.get("type")
        if a_type == "release":
            add({
                "type": "release",
                "title": a.get("title") or "Release",
                "summary": (a.get("metadata") or {}).get("tag"),
                "occurred_at": a.get("occurred_at"),
                "confidence": 1.0,
                "provenance": "observed",
                "artifact_ids": [a["provider_id"]],
                "source_url": a.get("source_url"),
            })
        elif a_type == "pr":
            meta = a.get("metadata") or {}
            if meta.get("merged_at") or meta.get("state") == "closed":
                add({
                    "type": "pr",
                    "title": a.get("title") or "Pull request",
                    "summary": f"PR #{meta.get('number')} ({meta.get('state')})",
                    "occurred_at": a.get("occurred_at"),
                    "confidence": 1.0,
                    "provenance": "observed",
                    "artifact_ids": [a["provider_id"]],
                    "source_url": a.get("source_url"),
                })
        elif a_type == "issue":
            meta = a.get("metadata") or {}
            if meta.get("state") == "closed":
                add({
                    "type": "issue",
                    "title": a.get("title") or "Issue",
                    "summary": f"Issue #{meta.get('number')} closed",
                    "occurred_at": a.get("occurred_at"),
                    "confidence": 1.0,
                    "provenance": "observed",
                    "artifact_ids": [a["provider_id"]],
                    "source_url": a.get("source_url"),
                })

    # Commit clusters
    commits = [a for a in artifacts if a.get("type") == "commit"]
    for cluster in cluster_commits(commits):
        add({
            "type": "commit_cluster",
            "title": cluster["title"],
            "summary": f"{cluster['commit_count']} commits in {cluster['components']}",
            "occurred_at": cluster["occurred_at"],
            "end_at": cluster["end_at"],
            "confidence": cluster["confidence"],
            "provenance": cluster["provenance"],
            "metadata_json": {
                "commit_count": cluster["commit_count"],
                "commit_ids": cluster["commit_ids"],
                "components": cluster["components"],
                "paths": cluster["paths"],
            },
            "artifact_ids": cluster["commit_ids"],
            "source_urls": cluster["source_urls"],
        })

    # Dependency change candidates
    for dc in _detect_dependency_changes(file_changes):
        add(dc)

    # User decisions / experiments (pass-through, provenance user)
    for d in decisions or []:
        add({
            "type": "decision",
            "title": d.get("title", "Decision"),
            "summary": "Decision record",
            "occurred_at": d.get("decided_at"),
            "confidence": 1.0,
            "provenance": "user",
            "metadata_json": {"decision_id": d.get("id"), "status": d.get("status")},
            "artifact_ids": [f"decision:{d.get('id')}"] if d.get("id") else [],
        })
    for e in experiments or []:
        add({
            "type": "experiment",
            "title": e.get("title", "Experiment"),
            "summary": "Failed experiment archive",
            "occurred_at": e.get("evaluated_at") or e.get("start_at"),
            "confidence": 1.0,
            "provenance": "user",
            "metadata_json": {"experiment_id": e.get("id"), "decision": e.get("decision")},
            "artifact_ids": [f"experiment:{e.get('id')}"] if e.get("id") else [],
        })

    events.sort(key=lambda e: e.get("occurred_at") or "", reverse=True)
    return events


def _detect_dependency_changes(file_changes: list[dict]) -> list[dict]:
    candidates = []
    manifest_files = {
        "package.json", "pyproject.toml", "requirements.txt", "go.mod",
        "Cargo.toml", "Gemfile", "composer.json", "pom.xml", "build.gradle",
    }
    for fc in file_changes:
        path = fc.get("file_path", "")
        name = path.rsplit("/", 1)[-1] if "/" in path else path
        if name in manifest_files and fc.get("change_type") in ("modified", "added"):
            candidates.append({
                "type": "dependency_change",
                "title": f"Dependency manifest changed: {name}",
                "summary": f"{name} was {fc.get('change_type')} ({fc.get('additions', 0)}+/{fc.get('deletions', 0)}-)",
                "occurred_at": fc.get("occurred_at"),
                "confidence": 0.75,
                "provenance": "rule-derived",
                "metadata_json": {"file_path": path, "change_type": fc.get("change_type")},
                "artifact_ids": [f"file:{path}"],
                "source_urls": [],
            })
    return candidates


def detect_change_candidates(file_changes: list[dict]) -> list[dict]:
    """Suggest candidate events for user confirmation (Suggested provenance)."""
    candidates = []
    grouped: dict[str, list[dict]] = {}
    for fc in file_changes:
        grouped.setdefault(fc.get("file_path", ""), []).append(fc)

    for path, changes in grouped.items():
        added = any(c.get("change_type") == "added" for c in changes)
        removed = any(c.get("change_type") == "deleted" for c in changes)
        name = path.rsplit("/", 1)[-1]
        is_test_file = path.endswith(("_test.py", ".test.ts", ".test.tsx", ".spec.js", ".test.js", ".spec.ts")) or name.startswith("test_")
        if is_test_file and added and not removed:
            candidates.append({
                "type": "test_infrastructure_introduced",
                "title": f"Test infrastructure introduced: {path}",
                "summary": "New test file detected",
                "occurred_at": changes[0].get("occurred_at"),
                "confidence": 0.8,
                "provenance": "suggested",
                "metadata_json": {"file_path": path},
            })
        if removed and any(c.get("change_type") == "added" for c in changes):
            candidates.append({
                "type": "short_lived_code_removed",
                "title": f"Code removed after introduction: {path}",
                "summary": "Added then removed within snapshot history window",
                "occurred_at": changes[0].get("occurred_at"),
                "confidence": 0.6,
                "provenance": "suggested",
                "metadata_json": {"file_path": path},
            })
    return candidates