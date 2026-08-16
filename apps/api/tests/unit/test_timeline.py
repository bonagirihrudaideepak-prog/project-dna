"""Unit tests for timeline clustering and change detection."""

from datetime import datetime, timedelta

from app.analysis.timeline.builder import (
    cluster_commits,
    detect_change_candidates,
    detect_component_overlap,
)

def _commit(day_offset: int, title: str, paths: list[str], provider_id: str) -> dict:
    dt = (datetime(2026, 1, 10) + timedelta(days=day_offset)).isoformat() + "Z"
    return {
        "provider_id": provider_id,
        "title": title,
        "occurred_at": dt,
        "source_url": f"https://example.com/{provider_id}",
        "metadata": {"paths": paths},
    }


def test_component_overlap():
    assert detect_component_overlap({"api"}, {"api"}) == 1.0
    assert detect_component_overlap({"api"}, {"db"}) == 0.0


def test_cluster_splits_on_time_gap():
    commits = [
        _commit(0, "feat: a", ["src/api/a.py"], "c1"),
        _commit(1, "feat: b", ["src/api/b.py"], "c2"),
        _commit(20, "feat: c", ["src/api/c.py"], "c3"),
    ]
    clusters = cluster_commits(commits)
    assert len(clusters) == 2
    assert clusters[0]["commit_count"] == 2
    assert clusters[1]["commit_count"] == 1


def test_change_candidates_detect_test_introduction():
    changes = [
        {"file_path": "src/test_app.py", "change_type": "added", "additions": 5, "deletions": 0},
        {"file_path": "src/app.py", "change_type": "modified", "additions": 5, "deletions": 0},
    ]
    candidates = detect_change_candidates(changes)
    assert any(c["type"] == "test_infrastructure_introduced" for c in candidates)


def test_change_candidates_detect_short_lived_code():
    changes = [
        {"file_path": "src/feature.py", "change_type": "added", "additions": 10, "deletions": 0},
        {"file_path": "src/feature.py", "change_type": "deleted", "additions": 0, "deletions": 10},
    ]
    candidates = detect_change_candidates(changes)
    assert any(c["type"] == "short_lived_code_removed" for c in candidates)
