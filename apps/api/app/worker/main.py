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

import time
from datetime import datetime, timedelta

from sqlalchemy import text

from ..config import settings
from ..db import SessionLocal, engine
from ..github.adapter import GitHubAdapter
from ..models import AnalysisJob, RepositorySnapshot
from ..services.analysis import FixtureSource, run_snapshot_analysis

JOB_LEASE_SECONDS = 600
POLL_SECONDS = 3
MAX_ATTEMPTS = 3
DEAD_MAN_SWITCH_SECONDS = 300  # reclaim if no heartbeat within 5 min

CLAIM_SQL = text("""
SELECT j.id
FROM analysis_jobs j
WHERE j.state IN ('QUEUED', 'RETRY')
  AND j.attempts < :max_attempts
  AND (j.lease_until IS NULL OR j.lease_until < :now)
ORDER BY j.created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED
""")


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
    return GitHubAdapter(token=settings.github_token)


def _claim_job() -> AnalysisJob | None:
    with engine.begin() as conn:
        row = conn.execute(CLAIM_SQL, {"max_attempts": MAX_ATTEMPTS, "now": datetime.utcnow()}).first()
        if not row:
            return None
        conn.execute(
            text("UPDATE analysis_jobs SET state='RUNNING', lease_until=:lease WHERE id=:id"),
            {"lease": datetime.utcnow() + timedelta(seconds=JOB_LEASE_SECONDS), "id": row[0]},
        )
        job_id = row[0]
    db = SessionLocal()
    try:
        return db.get(AnalysisJob, job_id)
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
            job.lease_until = datetime.utcnow() + timedelta(seconds=JOB_LEASE_SECONDS)
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
        return datetime.utcnow() > deadline
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
        age = (datetime.utcnow() - job.lease_until).total_seconds()
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
        job.lease_until = datetime.utcnow() + timedelta(seconds=JOB_LEASE_SECONDS)
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


def worker_once() -> int:
    job = _claim_job()
    if not job:
        return 0
    job_id = str(job.id)
    try:
        _run_job(job)
        print(f"[worker] completed {job_id}", flush=True)
        return 1
    except Exception as exc:  # noqa: BLE001
        db = SessionLocal()
        try:
            j = db.get(AnalysisJob, job_id)
            if j:
                # Check dead man's switch: if lease is stale, treat as failure
                if _dead_man_switch(job_id):
                    j.state = "FAILED"
                    j.error_code = "DEAD_MAN_SWITCH"
                    j.error_detail = "Job lease stale; no heartbeat received within window"
                elif j.attempts >= MAX_ATTEMPTS or _deadline_passed(job_id):
                    j.state = "FAILED"
                    j.error_code = getattr(exc, "code", "WORKER_FAILED")
                    j.error_detail = str(exc)[:2000]
                    snapshot = db.get(RepositorySnapshot, j.snapshot_id)
                    if snapshot and snapshot.status != "COMPLETED":
                        snapshot.status = "FAILED"
                else:
                    j.state = "RETRY"
                    j.error_code = getattr(exc, "code", "WORKER_FAILED")
                    j.error_detail = str(exc)[:2000]
                j.finished_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()
        print(f"[worker] failed {job_id}: {exc}", flush=True)
        return 1


def run_forever():
    print(f"[worker] started (fixture_root={settings.fixture_root})", flush=True)
    while True:
        try:
            processed = worker_once()
            if not processed:
                time.sleep(POLL_SECONDS)
        except Exception as exc:  # noqa: BLE001
            print(f"[worker] loop error: {exc}", flush=True)
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run_forever()
