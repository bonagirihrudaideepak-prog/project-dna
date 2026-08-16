"""Analysis orchestrator: runs the full pipeline for a snapshot and persists
results transactionally."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..analysis.graph.builder import build_graph
from ..analysis.inspector import inspect_directory, inspect_zip
from ..analysis.scoring.pipeline import run_pipeline
from ..analysis.timeline.builder import build_timeline_events
from ..config import settings
from ..github.adapter import GitHubAdapter
from ..models import (
    AnalysisJob,
    Artifact,
    DNAScore,
    FileChange,
    FileRecord,
    GraphEdge,
    GraphNode,
    MetricValue,
    RepositorySnapshot,
    TimelineEvent,
)


class FixtureSource:
    """Reads a fixture repository from disk (deterministic, offline)."""

    def __init__(self, root: Path):
        self.root = root

    async def repository(self, full_name: str) -> dict[str, Any]:
        manifest = json.loads((self.root / "manifest.json").read_text())
        return {
            "github_repo_id": manifest.get("github_repo_id"),
            "full_name": manifest.get("full_name") or full_name,
            "owner": manifest.get("owner", "fixture"),
            "name": manifest.get("name"),
            "visibility": "public",
            "default_branch": manifest.get("default_branch", "main"),
            "description": manifest.get("description"),
        }

    async def default_branch_sha(self, full_name: str, branch: str) -> str:
        manifest = json.loads((self.root / "manifest.json").read_text())
        return manifest.get("commit_sha", "fixture-" + full_name.split("/")[-1][:32])

    async def artifacts(self, full_name: str, branch: str, limit: int) -> list[dict]:
        path = self.root / "artifacts.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text())
        data = data[:limit]
        out = []
        for a in data:
            out.append({
                "type": a.get("type"),
                "provider_id": a.get("provider_id"),
                "title": a.get("title"),
                "occurred_at": a.get("occurred_at"),
                "source_url": a.get("source_url"),
                "metadata": a.get("metadata", {}),
            })
        return out

    def inspect(self) -> Any:
        return inspect_directory(self.root / "repo", settings.analysis_max_file_bytes)

    def file_changes(self) -> list[dict]:
        path = self.root / "file_changes.json"
        if not path.exists():
            return []
        return json.loads(path.read_text())


def _artifact_dict(a: Any, limit_fields: bool = True) -> dict:
    meta = dict(a.metadata)
    if limit_fields:
        for k in ("message", "body"):
            if k in meta and isinstance(meta[k], str) and len(meta[k]) > 1000:
                meta[k] = meta[k][:1000]
    return {
        "type": a.type,
        "provider_id": a.provider_id,
        "title": a.title,
        "occurred_at": a.occurred_at,
        "source_url": a.source_url,
        "metadata": meta,
    }


def _read_archive(tempdir: Path, archive: bytes) -> Path:
    from ..analysis.inspector import (
        MAX_ENTRIES,
        MAX_EXPANDED_BYTES,
        UnsafeArchiveError,
        safe_join,
    )

    zip_path = tempdir / "repo.zip"
    zip_path.write_bytes(archive)
    extract_dir = tempdir / "repo"
    extract_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        infolist = zf.infolist()
        if len(infolist) > MAX_ENTRIES:
            raise UnsafeArchiveError("Archive entry count exceeds safety limit")
        total = 0
        for info in infolist:
            total += info.file_size
            if total > MAX_EXPANDED_BYTES:
                raise UnsafeArchiveError("Archive expansion exceeds safety limit")
            target = safe_join(extract_dir, info.filename)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
    # GitHub zips wrap content in a single top-level dir; normalize to repo/
    children = list(extract_dir.iterdir())
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extract_dir


def run_snapshot_analysis(db: Session, snapshot_id: str, source: Any, heartbeat: Any = None) -> dict[str, Any]:
    """Execute the pipeline for one snapshot and return a status summary.

    `heartbeat` is an optional zero-arg callable (the worker uses it to refresh
    the job lease during long phases so the job is never reclaimed mid-run)."""
    snapshot = db.get(RepositorySnapshot, snapshot_id)
    if not snapshot:
        raise ValueError(f"Snapshot {snapshot_id} not found")
    job = (
        db.query(AnalysisJob).filter(AnalysisJob.snapshot_id == snapshot_id).order_by(AnalysisJob.created_at).first()
    )
    if not job:
        job = AnalysisJob(snapshot_id=snapshot_id, state="QUEUED")
        db.add(job)

    project = snapshot.project
    warnings: list[str] = []

    def progress(state: str, phase: str, pct: int):
        job.state = state
        job.phase = phase
        job.progress = pct
        db.commit()
        if heartbeat:
            heartbeat()

    try:
        progress("FETCHING", "metadata", 5)
        full_name = project.full_name
        branch = project.default_branch

        if isinstance(source, FixtureSource):
            sha = asyncio_sync(source.default_branch_sha, full_name, branch)
            artifacts = asyncio_sync(source.artifacts, full_name, branch, settings.analysis_max_commits)
            inspection = source.inspect()
            file_changes = source.file_changes()
            for w in inspection.warnings:
                warnings.append(w)
        else:
            sha = asyncio_sync(source.default_branch_sha, full_name, branch)
            artifacts = asyncio_sync(source.artifacts, full_name, branch, settings.analysis_max_commits)
            inspection, file_changes = _github_inspect(source, full_name, sha, branch)
            for w in inspection.warnings:
                warnings.append(w)

        snapshot.commit_sha = sha
        snapshot.captured_at = datetime.utcnow()
        db.commit()

        # --- persist artifacts
        progress("EXTRACTING", "artifacts", 25)
        for a in artifacts:
            db.add(Artifact(
                snapshot_id=snapshot.id,
                type=a.get("type", "unknown"),
                provider_id=a.get("provider_id", ""),
                title=a.get("title"),
                occurred_at=_parse_dt(a.get("occurred_at")),
                source_url=a.get("source_url"),
                metadata_json=a.get("metadata", {}),
            ))
        db.commit()

        # --- persist files
        for f in inspection.files:
            db.add(FileRecord(
                snapshot_id=snapshot.id,
                path=f.path,
                extension=f.extension,
                language=f.language,
                bytes=f.bytes,
                lines=f.lines,
                category=f.category,
                content_hash=f.content_hash,
                is_generated=f.is_generated,
            ))
        db.commit()

        # --- persist file changes
        for fc in file_changes:
            db.add(FileChange(
                snapshot_id=snapshot.id,
                commit_artifact_id=fc.get("commit_artifact_id"),
                file_path=fc.get("file_path", ""),
                additions=int(fc.get("additions", 0)),
                deletions=int(fc.get("deletions", 0)),
                change_type=fc.get("change_type", "modified"),
                occurred_at=_parse_dt(fc.get("occurred_at")),
            ))
        db.commit()

        # --- metrics + scoring
        progress("SCORING", "indicators", 55)
        decisions = _load_decisions(db, project.id)
        experiments = _load_experiments(db, project.id)
        decision_counts = {
            "decisions": len(decisions),
            "reviews": sum(1 for d in decisions if d.get("outcome_reviews")),
            "experiments": len(experiments),
        }
        scores = run_pipeline(inspection, artifacts, file_changes, decision_counts)

        for score in scores:
            metric_refs = {}
            # store indicator metric values
            metric_ids = {}
            for ind_key, ind in score.indicators.items():
                mv = MetricValue(
                    snapshot_id=snapshot.id,
                    key=f"{score.dimension}:{ind_key}",
                    raw_value_json=_safe_json(ind.raw),
                    normalized_value=ind.normalized_value,
                    evidence_json={"evidence_ids": ind.evidence_ids[:50]},
                )
                db.add(mv)
                db.flush()
                metric_ids[ind_key] = mv.id
            db.flush()

            score_row = DNAScore(
                snapshot_id=snapshot.id,
                dimension=score.dimension,
                score=score.score,
                coverage=score.coverage,
                confidence=score.confidence,
                direction=score.direction,
                model_version=score.model_version,
                explanation_json=score.to_dict(),
            )
            db.add(score_row)
            db.flush()
            for ind_key, ind in score.indicators.items():
                mv_id = metric_ids.get(ind_key)
                if mv_id:
                    metric_refs[mv_id] = ind
            score_row.explanation_json = score.to_dict()
            db.commit()

        # --- timeline
        progress("BUILDING_VIEWS", "timeline", 80)
        events = build_timeline_events(
            artifacts,
            file_changes,
            decisions=[{**d, "id": str(d["id"])} for d in decisions],
            experiments=[{**e, "id": str(e["id"])} for e in experiments],
        )
        for ev in events:
            row = TimelineEvent(
                snapshot_id=snapshot.id,
                project_id=project.id,
                type=ev.get("type", "event"),
                title=ev.get("title", "Event"),
                summary=ev.get("summary"),
                occurred_at=_parse_dt(ev.get("occurred_at")),
                end_at=_parse_dt(ev.get("end_at")),
                confidence=float(ev.get("confidence", 1.0)),
                provenance=ev.get("provenance", "observed"),
                metadata_json=ev.get("metadata_json", {}) | {"artifact_ids": ev.get("artifact_ids", [])},
            )
            db.add(row)
        db.commit()

        # --- graph
        _build_and_store_graph(db, project.id, snapshot, events)

        snapshot.status = "COMPLETED"
        snapshot.warning_json = {"warnings": warnings}
        job.state = "COMPLETED"
        job.progress = 100
        job.phase = "finalize"
        job.finished_at = datetime.utcnow()
        db.commit()
        return {"status": "COMPLETED", "warnings": warnings, "event_count": len(events)}

    except Exception as exc:  # noqa: BLE001
        db.rollback()
        job.state = "FAILED"
        job.error_code = getattr(exc, "code", "ANALYSIS_FAILED")
        job.error_detail = str(exc)[:2000]
        job.finished_at = datetime.utcnow()
        # Snapshot status is left to the worker so retryable failures can retry
        # against a snapshot that is still PENDING rather than stuck FAILED.
        db.commit()
        raise


def _safe_json(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return {"repr": str(obj)}


def _parse_dt(value: Any):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _load_decisions(db: Session, project_id: str) -> list[dict]:
    from ..models import Decision, OutcomeReview
    from sqlalchemy.orm import selectinload

    rows = (
        db.query(Decision)
        .options(selectinload(Decision.outcome_reviews))
        .filter(Decision.project_id == project_id, Decision.archived.is_(False))
        .all()
    )
    out = []
    for d in rows:
        out.append({
            "id": str(d.id),
            "title": d.title,
            "status": d.status,
            "decided_at": d.decided_at.isoformat() if d.decided_at else None,
            "expected_impact": d.expected_impact,
            "outcome_reviews": [{"id": str(r.id), "verdict": r.verdict} for r in d.outcome_reviews],
        })
    return out


def _load_experiments(db: Session, project_id: str) -> list[dict]:
    from ..models import Experiment

    rows = db.query(Experiment).filter(Experiment.project_id == project_id, Experiment.archived.is_(False)).all()
    return [
        {
            "id": str(e.id),
            "title": e.title,
            "decision": e.decision,
            "start_at": e.start_at.isoformat() if e.start_at else None,
            "evaluated_at": e.evaluated_at.isoformat() if e.evaluated_at else None,
        }
        for e in rows
    ]


def _build_and_store_graph(db: Session, project_id: str, snapshot: RepositorySnapshot, events: list[dict]):
    project = snapshot.project
    decisions = _load_decisions(db, project_id)
    experiments = _load_experiments(db, project_id)
    nodes, edges = build_graph(
        {"id": str(project.id), "full_name": project.full_name, "name": project.name},
        {
            "id": str(snapshot.id),
            "commit_sha": snapshot.commit_sha,
            "status": snapshot.status,
            "captured_at": snapshot.captured_at.isoformat() if snapshot.captured_at else None,
        },
        events,
        decisions,
        experiments,
    )
    for n in nodes:
        db.add(GraphNode(
            project_id=project_id,
            snapshot_id=snapshot.id,
            node_type=n["node_type"],
            entity_type=n["entity_type"],
            entity_id=str(n["entity_id"])[:64],
            label=n["label"][:500],
            metadata_json=n["metadata_json"],
        ))
    db.flush()
    node_keys: dict[str, GraphNode] = {}
    rows = db.query(GraphNode).filter(GraphNode.snapshot_id == snapshot.id).all()
    for r in rows:
        node_keys[f"{r.entity_type}:{r.entity_id}"] = r
    for e in edges:
        src = node_keys.get(e["source"])
        tgt = node_keys.get(e["target"])
        if src and tgt:
            db.add(GraphEdge(
                project_id=project_id,
                source_node_id=src.id,
                target_node_id=tgt.id,
                edge_type=e["edge_type"],
                provenance=e["provenance"],
                confidence=e["confidence"],
                evidence_json=e["evidence_json"],
            ))
    db.commit()


def _github_inspect(source: GitHubAdapter, full_name: str, sha: str, branch: str):
    from ..analysis.inspector import inspect_zip
    from ..github.adapter import GitHubArtifact

    archive = asyncio_sync(source.archive_bytes, full_name, sha)
    tempdir = Path(tempfile.mkdtemp(prefix="project-dna-"))
    try:
        repo_dir = _read_archive(tempdir, archive)
        inspection = inspect_zip(archive, settings.analysis_max_file_bytes)
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)

    # derive file_changes from commit history (best-effort; use archive + artifacts)
    file_changes: list[dict] = []
    return inspection, file_changes


def asyncio_sync(coro_fn, *args):
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            return pool.submit(asyncio.run, coro_fn(*args)).result()
    return asyncio.run(coro_fn(*args))