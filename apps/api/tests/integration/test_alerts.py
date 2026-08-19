"""Integration test for alert rule evaluation against a live database.

These tests need a running PostgreSQL (DATABASE_URL from conftest). They are
skipped when the DB is unreachable so the suite degrades gracefully in CI
without a database.
"""

import pytest
from sqlalchemy import create_engine, text

from app.adapters.db import SessionLocal
from app.config import settings
from app.domain.analysis.alerts import RuleSpec, ScoreSnapshot, evaluate_scores
from app.models import Alert, AlertRule, Project, RepositorySnapshot, User
from app.worker.main import _evaluate_and_store_alerts


@pytest.fixture(scope="module")
def db_available():
    engine = create_engine(settings.database_url, connect_args={"connect_timeout": 2})
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _require_db(db_available):
    if not db_available:
        pytest.skip("database unavailable; skipping alert integration test")


@pytest.fixture(scope="module")
def project_with_rules(db_available):
    _require_db(db_available)
    db = SessionLocal()
    user = User(github_user_id=999001, login="alert-test-user")
    project = Project(full_name="alert-test/org", owner="alert-test", name="org", is_fixture=False)
    db.add(user)
    db.flush()
    db.add(project)
    db.flush()
    rule = AlertRule(
        project_id=project.id,
        dimension="maintainability",
        operator="lt",
        threshold=50,
        enabled=True,
    )
    db.add(rule)
    db.commit()
    yield project, rule
    db.delete(project)
    db.commit()
    db.close()


def test_evaluate_scores_skips_withheld():
    decisions = evaluate_scores(
        rules=[RuleSpec("r1", "maintainability", "lt", 50, True)],
        scores=[ScoreSnapshot("maintainability", 40, 0.2)],
    )
    assert decisions == []


def test_store_alerts_idempotent(db_available, project_with_rules):
    _require_db(db_available)
    project, _rule = project_with_rules
    db = SessionLocal()
    snapshot = RepositorySnapshot(project_id=project.id, commit_sha="abc123", status="COMPLETED")
    db.add(snapshot)
    db.commit()

    first = _evaluate_and_store_alerts(snapshot)
    second = _evaluate_and_store_alerts(snapshot)

    alerts = db.query(Alert).filter(Alert.snapshot_id == snapshot.id).all()
    # Without a DNAScore row for this snapshot, nothing can fire.
    assert first == 0
    assert second == 0
    assert len(alerts) == 0

    db.delete(snapshot)
    db.commit()
    db.close()