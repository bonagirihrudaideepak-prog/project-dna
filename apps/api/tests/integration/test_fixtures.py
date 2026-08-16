"""Integration test: full analysis job against the mature fixture."""

import json
import os
from pathlib import Path

from sqlalchemy.orm import Session

from app.analysis.inspector import inspect_directory
from app.analysis.scoring.pipeline import run_pipeline
from app.models import DNAScore

FIXTURE_ROOT = Path(os.environ["FIXTURE_ROOT"])


def _load_fixture(name: str):
    root = FIXTURE_ROOT / name
    manifest = json.loads((root / "manifest.json").read_text())
    artifacts = json.loads((root / "artifacts.json").read_text())
    file_changes = json.loads((root / "file_changes.json").read_text())
    inspection = inspect_directory(root / "repo", 1024 * 1024)
    return manifest, artifacts, file_changes, inspection


def test_mature_fixture_produces_expected_dimensions():
    _, artifacts, file_changes, inspection = _load_fixture("synthetic-mature-repo")
    scores = run_pipeline(inspection, artifacts, file_changes)
    keys = {s.dimension for s in scores}
    assert keys == {
        "technical_complexity", "maintainability", "testing_maturity",
        "documentation_quality", "evolution_health", "delivery_readiness",
        "scalability_readiness", "technical_debt_risk",
    }
    for s in scores:
        assert s.model_version == "dna-core-1.0"


def test_mature_fixture_has_evidence_for_key_dimensions():
    _, artifacts, file_changes, inspection = _load_fixture("synthetic-mature-repo")
    scores = run_pipeline(inspection, artifacts, file_changes)
    by_key = {s.dimension: s for s in scores}
    # mature fixture should produce a real score for maintainability
    assert by_key["maintainability"].score is not None
    # and the timeline-relevant evolution indicators should have evidence
    evo = by_key["evolution_health"]
    assert "traceable_change_units" in evo.indicators


def test_minimal_fixture_mostly_withheld():
    _, artifacts, file_changes, inspection = _load_fixture("synthetic-minimal-repo")
    scores = run_pipeline(inspection, artifacts, file_changes)
    # minimal fixture has thin evidence: most dimensions withheld
    scored = [s for s in scores if s.score is not None]
    assert len(scored) < len(scores)
    # never a zero score from missing evidence
    for s in scores:
        if s.score is None:
            assert s.confidence == "insufficient"


def test_evolution_fixture_detects_rework():
    _, artifacts, file_changes, inspection = _load_fixture("synthetic-evolution-repo")
    scores = run_pipeline(inspection, artifacts, file_changes)
    by_key = {s.dimension: s for s in scores}
    # evolution fixture has a rework hotspot in router.py
    debt = by_key["technical_debt_risk"]
    assert debt.indicators["hotspot_concentration"].raw is not None
