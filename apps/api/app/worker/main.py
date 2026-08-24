"""PostgreSQL-backed analysis worker.

Claims jobs with SELECT ... FOR UPDATE SKIP LOCKED, runs the pipeline, and
stores results. Keeps long analysis out of HTTP requests.

Failure semantics:
- Lease heartbeat is refreshed on every progress update, so a long job is never
  reclaimed by another worker.
- A job that exceeds the configured analysis timeout is failed (deadline).
- Retryable failures go to RETRY up to MAX_ATTEMPTS; the snapshot only flips to
  FAILED once attempts are exhausted.
- A "dead man's switch" monitor checks lease freshness; if a job's lease expires
  without a progress update, it is reclaimed by another worker.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from ..adapters import metrics
from ..adapters.cache_service import CacheService
from ..adapters.db import SessionLocal, engine
from ..adapters.github import GitHubAdapter
from ..adapters.security import decrypt_token
from ..application.analysis import FixtureSource, run_snapshot_analysis
from ..config import settings
from ..config.constants import (
    JOB_STATE_COMPLETED,
    JOB_STATE_FAILED,
    JOB_STATE_QUEUED,
    JOB_STATE_RETRY,
    JOB_STATE_RUNNING,
)
from ..domain.analysis.alerts import RuleSpec, ScoreSnapshot, evaluate_scores
from ..models import (
    Alert,
    AlertRule,
    AnalysisJob,
    DNAScore,
    GitHubConnection,
    ProjectMembership,
    RepositorySnapshot,
)

# Module-level cache service (Redis-backed, degrades gracefully when Redis is down)
_cache_service = CacheService()

JOB_LEASE_SECONDS = 600
POLL_SECONDS = 3
MAX_ATTEMPTS = 3
DEAD_MAN_SWITCH_SECONDS = 300  # reclaim if no heartbeat within 5 min

CLAIM_SQL = text("""
SELECT j.id
FROM analysis_jobs j
WHERE j.state IN (:queued, :retry)
  AND j.attempts < :max_attempts
  AND (j.lease_until IS NULL OR j.lease_until < :now)
ORDER BY j.created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED
""")


def _project_token(project_id: str) -> str:
    """Resolve a GitHub token for a project.

    Priority: project owner's stored OAuth token (revoked connections skipped),
    then the server-level GITHUB_TOKEN. Returns "" when nothing is available.
    """
    db = SessionLocal()
    try:
        membership = (
            db.query(ProjectMembership)
            .filter(ProjectMembership.project_id == project_id, ProjectMembership.role == "owner")
            .first()
        )
        if membership:
            conn = (
                db.query(GitHubConnection)
                .filter(
                    GitHubConnection.user_id == membership.user_id,
                    GitHubConnection.revoked_at.is_(None),
                )
                .first()
            )
            if conn:
                try:
                    return decrypt_token(conn.encrypted_token)
                except Exception:
                    pass
    finally:
        db.close()
    return settings.github_token or ""


def _make_source(snapshot: RepositorySnapshot):
    project = snapshot.project
    if project.is_fixture:
        from pathlib import Path

        root = Path(settings.fixture_root)
        for d in root.iterdir():
            manifest = d / "manifest.json"
            if manifest.exists():
                import json

                try:
                    if json.loads(manifest.read_text()).get("full_name") == project.full_name:
                        return FixtureSource(d)
                except Exception:
                    continue
        raise RuntimeError(f"No fixture found for {project.full_name}")
    token = _project_token(str(project.id))
    if not token:
        raise RuntimeError(
            f"No GitHub token available for {project.full_name}; connect GitHub or set GITHUB_TOKEN"
        )
    return GitHubAdapter(token=token)


def _claim_job() -> AnalysisJob | None:
    with engine.begin() as conn:
        row = conn.execute(CLAIM_SQL, {"max_attempts": MAX_ATTEMPTS, "now": datetime.now(timezone.utc), "queued": JOB_STATE_QUEUED, "retry": JOB_STATE_RETRY}).first()
        if not row:
            return None
        conn.execute(
            text("UPDATE analysis_jobs SET state=:running, lease_until=:lease WHERE id=:id"),
            {"lease": datetime.now(timezone.utc) + timedelta(seconds=JOB_LEASE_SECONDS), "id": row[0], "running": JOB_STATE_RUNNING},
        )
        job_id = row[0]
    db = SessionLocal()
    try:
        job = db.get(AnalysisJob, job_id)
        if job is not None:
            print(f"[worker] claimed {job_id} (attempts={job.attempts})", flush=True)
        return job
    finally:
        db.close()


def _refresh_lease(job_id: str, phase: str | None = None, progress: int | None = None):
    """Refresh lease (and optionally phase/progress) so the job isn't reclaimed."""
    db = SessionLocal()
    try:
        job = db.get(AnalysisJob, job_id)
        if job:
            if phase is not None:
                job.phase = phase
            if progress is not None:
                job.progress = progress
            job.lease_until = datetime.now(timezone.utc) + timedelta(seconds=JOB_LEASE_SECONDS)
            db.commit()
    finally:
        db.close()


def _deadline_passed(job_id: str) -> bool:
    """True if the job has been running past the configured analysis timeout."""
    db = SessionLocal()
    try:
        job = db.get(AnalysisJob, job_id)
        if not job or not job.created_at:
            return False
        deadline = job.created_at + timedelta(seconds=settings.analysis_timeout_seconds)
        return datetime.now(timezone.utc) > deadline
    finally:
        db.close()


def _dead_man_switch(job_id: str) -> bool:
    """True if the job hasn't had a heartbeat (lease refresh) in too long.

    This prevents a crashed worker from leaving a job stuck RUNNING forever."""
    db = SessionLocal()
    try:
        job = db.get(AnalysisJob, job_id)
        if not job or not job.lease_until:
            return True  # no lease = treat as dead
        # If lease has expired, the normal claim logic will reclaim it,
        # but check if we're close to the dead man switch window.
        age = (datetime.now(timezone.utc) - job.lease_until).total_seconds()
        return age > DEAD_MAN_SWITCH_SECONDS
    finally:
        db.close()


def _run_job(job: AnalysisJob):
    db = SessionLocal()
    try:
        snapshot = db.get(RepositorySnapshot, job.snapshot_id)
        if not snapshot:
            raise RuntimeError("Snapshot missing")
        job.attempts += 1
        job.lease_until = datetime.now(timezone.utc) + timedelta(seconds=JOB_LEASE_SECONDS)
        db.commit()
        _refresh_lease(job.id, "starting", 2)
        result = run_snapshot_analysis(
            db,
            str(snapshot.id),
            _make_source(snapshot),
            heartbeat=lambda: _refresh_lease(job.id),
        )
        return result
    finally:
        db.close()


def _queue_depth() -> int:
    with engine.connect() as conn:
        return (
            conn.execute(
                text("SELECT count(*) FROM analysis_jobs WHERE state IN (:q, :r)"), {"q": JOB_STATE_QUEUED, "r": JOB_STATE_RETRY}
            ).scalar()
            or 0
        )


def _evaluate_and_store_alerts(snapshot: RepositorySnapshot) -> int:
    """Evaluate alert rules against a completed snapshot and persist crossings.

    Regression-crossing semantics: an alert fires only when a score moves across
    the threshold relative to the previous comparable snapshot, so a dimension
    that stays bad does not re-fire. Idempotent: the (rule_id, snapshot_id)
    unique constraint means a re-run (worker retry, snapshot re-analysis) never
    double-fires. Returns the number of alerts created.
    """
    from ..config.constants import COVERAGE_INSUFFICIENT

    db = SessionLocal()
    try:
        rules = (
            db.query(AlertRule)
            .filter(AlertRule.project_id == snapshot.project_id, AlertRule.enabled.is_(True))
            .all()
        )
        if not rules:
            return 0
        scores = db.query(DNAScore).filter(DNAScore.snapshot_id == snapshot.id).all()
        # Build per-dimension history with ONE joined query over all earlier
        # snapshots of the project (oldest first, so the last non-null per
        # dimension wins) instead of one query per snapshot.
        earlier_scores = (
            db.query(DNAScore)
            .join(RepositorySnapshot, DNAScore.snapshot_id == RepositorySnapshot.id)
            .filter(
                RepositorySnapshot.project_id == snapshot.project_id,
                RepositorySnapshot.id != snapshot.id,
            )
            .order_by(RepositorySnapshot.created_at.asc())
            .all()
        )
        history: dict[str, int] = {}
        for sc in earlier_scores:
            if sc.coverage >= COVERAGE_INSUFFICIENT and sc.score is not None:
                history[sc.dimension] = sc.score
        decisions = evaluate_scores(
            rules=[RuleSpec(id=str(r.id), dimension=r.dimension, operator=r.operator, threshold=r.threshold, enabled=r.enabled) for r in rules],
            scores=[ScoreSnapshot(dimension=s.dimension, score=s.score, coverage=s.coverage) for s in scores],
            history=history,
        )
        # Idempotency check: batch-load already-fired rules for this snapshot.
        existing_rule_ids = {
            str(rule_id) for (rule_id,) in db.query(Alert.rule_id).filter(Alert.snapshot_id == snapshot.id).all()
        }
        created = 0
        for d in decisions:
            if d.rule_id in existing_rule_ids:
                continue
            db.add(
                Alert(
                    rule_id=d.rule_id,
                    snapshot_id=snapshot.id,
                    dimension=d.dimension,
                    old_value=d.old_value,
                    new_value=d.new_value,
                )
            )
            created += 1
        if created:
            db.commit()
        return created
    finally:
        db.close()


def _sweep_dead_snapshots(db, project_id: str) -> int:
    """Housekeeping: delete FAILED/abandoned-PENDING snapshots past the TTL.

    COMPLETED snapshots are never touched (scored history is product data).
    Jobs cascade with their snapshot."""
    from ..config.constants import DEAD_SNAPSHOT_TTL_DAYS

    cutoff = datetime.now(timezone.utc) - timedelta(days=DEAD_SNAPSHOT_TTL_DAYS)
    dead = (
        db.query(RepositorySnapshot)
        .filter(
            RepositorySnapshot.project_id == project_id,
            RepositorySnapshot.status.in_(["FAILED", "PENDING"]),
            RepositorySnapshot.created_at < cutoff,
        )
        .all()
    )
    for snap in dead:
        db.delete(snap)
    if dead:
        db.commit()
    return len(dead)


def worker_once() -> int:
    job = _claim_job()
    if not job:
        return 0
    job_id = str(job.id)
    project_id: str | None = None
    try:
        db = SessionLocal()
        try:
            snap = db.get(RepositorySnapshot, job.snapshot_id)
            if snap:
                project_id = str(snap.project_id)
            _run_job(job)
            metrics.jobs_completed.inc()
            if project_id:
                snap = db.get(RepositorySnapshot, job.snapshot_id)
                if snap:
                    alerts_created = _evaluate_and_store_alerts(snap)
                    if alerts_created:
                        print(f"[worker] {alerts_created} alert(s) fired for {job_id}", flush=True)
                _cache_service.invalidate_project(project_id)
            swept = _sweep_dead_snapshots(db, project_id) if project_id else 0
            if swept:
                print(f"[worker] swept {swept} dead snapshot(s) for {project_id}", flush=True)
            print(f"[worker] completed {job_id}", flush=True)
            return 1
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        import traceback

        metrics.jobs_failed.inc()
        tb_text = traceback.format_exc()
        print(f"[worker] failure detail: {type(exc).__name__}: {exc}", flush=True)
        if os.environ.get("WORKER_TRACEBACKS"):
            print(tb_text, flush=True)
        db = SessionLocal()
        try:
            j = db.get(AnalysisJob, job_id)
            if j:
                # The lease belonged to the execution that just died; without
                # clearing it a RETRY would sit unclaimable for up to
                # JOB_LEASE_SECONDS.
                j.lease_until = None
                # Check dead man's switch: if lease is stale, treat as failure
                if _dead_man_switch(job_id):
                    j.state = JOB_STATE_FAILED
                    j.error_code = "DEAD_MAN_SWITCH"
                    j.error_detail = "Job lease stale; no heartbeat received within window"
                elif j.attempts >= MAX_ATTEMPTS or _deadline_passed(job_id):
                    j.state = JOB_STATE_FAILED
                    j.error_code = getattr(exc, "code", "WORKER_FAILED")
                    # Keep the full traceback: str(exc) alone is useless for
                    # diagnosing async/lifecycle failures.
                    j.error_detail = (str(exc) + "\n" + tb_text)[-2000:]
                    snapshot = db.get(RepositorySnapshot, j.snapshot_id)
                    if snapshot and snapshot.status != JOB_STATE_COMPLETED:
                        snapshot.status = JOB_STATE_FAILED
                else:
                    j.state = JOB_STATE_RETRY
                    j.error_code = getattr(exc, "code", "WORKER_FAILED")
                    j.error_detail = str(exc)[:2000]
                j.finished_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()
        print(f"[worker] failed {job_id}: {exc}", flush=True)
        return 1


def run_forever():
    import faulthandler

    # Watchdog: one stack dump if a single poll-cycle blocks >5min (true hang);
    # repeats disabled so long legitimate phases stay quiet.
    faulthandler.dump_traceback_later(300, repeat=False)
    metrics.worker_online.set(1)
    print(f"[worker] started (fixture_root={settings.fixture_root})", flush=True)
    while True:
        try:
            processed = worker_once()
            metrics.queue_depth.set(_queue_depth())
            if not processed:
                time.sleep(POLL_SECONDS)
        except Exception as exc:  # noqa: BLE001
            print(f"[worker] loop error: {exc}", flush=True)
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run_forever()
