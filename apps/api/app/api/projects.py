"""Projects, repositories, snapshots, and analysis jobs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import optional_user, parse_id
from ..github.adapter import GitHubAdapter
from ..models import (
    AnalysisJob,
    Project,
    ProjectMembership,
    RepositorySnapshot,
    User,
)
from ..schemas import AnalysisJobOut, GitHubRepoOut, ImportProjectIn, ProjectOut, SnapshotOut
from ..services.analysis import FixtureSource

router = APIRouter(tags=["projects"])


def require_membership(db: Session, project_id: str, user_id: str | None) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if user_id and not db.query(ProjectMembership).filter_by(project_id=project.id, user_id=user_id).first():
        # fixture demo projects are world-readable in dev
        if project.is_fixture and settings.env == "development":
            return project
        raise HTTPException(status_code=403, detail="Not a member of this project")
    return project


def _snapshot_out(s: RepositorySnapshot) -> SnapshotOut:
    return SnapshotOut(
        id=str(s.id),
        project_id=str(s.project_id),
        commit_sha=s.commit_sha,
        analyzer_version=s.analyzer_version,
        score_model_version=s.score_model_version,
        status=s.status,
        captured_at=s.captured_at,
        warning_json=s.warning_json or {},
        limits_json=s.limits_json or {},
    )


@router.get("/github/repositories", response_model=list[GitHubRepoOut])
async def list_repositories(
    q: str = "",
    page: int = 1,
    per_page: int = 30,
    db: Session = Depends(get_db),
):
    """List accessible repositories. When no OAuth token is configured, list
    seeded fixture repositories for offline development."""
    token = settings.github_token
    if token:
        adapter = GitHubAdapter(token=token)
        try:
            data = await adapter.list_repositories(q=q, page=page, per_page=per_page)
            items = data.get("items", [])
            out = []
            for it in items:
                out.append(GitHubRepoOut(
                    github_repo_id=it.get("id"),
                    full_name=it.get("full_name"),
                    owner=it.get("owner", {}).get("login", ""),
                    name=it.get("name", ""),
                    visibility=it.get("visibility", "public"),
                    default_branch=it.get("default_branch", "main"),
                    description=it.get("description"),
                ))
            return out
        finally:
            await adapter.close()

    # Fixture fallback
    fixture_root = Path(settings.fixture_root)
    out = []
    if fixture_root.exists():
        for d in sorted(fixture_root.iterdir()):
            manifest = d / "manifest.json"
            if manifest.exists():
                try:
                    data = json.loads(manifest.read_text())
                    out.append(GitHubRepoOut(**data))
                except Exception:
                    continue
    if not out:
        raise HTTPException(status_code=503, detail="No GitHub token and no fixtures available")
    return out


@router.post("/projects/import", response_model=ProjectOut)
async def import_project(body: ImportProjectIn, db: Session = Depends(get_db)):
    full_name = body.full_name.strip().lstrip("/")
    parts = full_name.split("/")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Expected owner/repo")

    existing = db.query(Project).filter(Project.full_name == full_name).first()
    if existing:
        return _project_out(existing, db)

    project = Project(
        full_name=full_name,
        owner=parts[0],
        name=parts[1],
        default_branch=body.branch or "main",
        visibility="public",
        is_fixture=_is_fixture(full_name),
    )
    db.add(project)
    db.flush()
    # attach current user as owner if authenticated
    db.commit()
    return _project_out(project, db)


def _is_fixture(full_name: str) -> bool:
    fixture_root = Path(settings.fixture_root)
    if not fixture_root.exists():
        return False
    for d in fixture_root.iterdir():
        if (d / "manifest.json").exists():
            try:
                if json.loads((d / "manifest.json").read_text()).get("full_name") == full_name:
                    return True
            except Exception:
                continue
    return False


def _project_out(project: Project, db: Session) -> ProjectOut:
    latest = (
        db.query(RepositorySnapshot)
        .filter(RepositorySnapshot.project_id == project.id)
        .order_by(RepositorySnapshot.created_at.desc())
        .first()
    )
    return ProjectOut(
        id=str(project.id),
        full_name=project.full_name,
        owner=project.owner,
        name=project.name,
        visibility=project.visibility,
        default_branch=project.default_branch,
        description=project.description,
        is_fixture=project.is_fixture,
        latest_snapshot=_snapshot_out(latest).model_dump() if latest else None,
    )


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(user_id: str | None = Depends(optional_user), db: Session = Depends(get_db), page: int = 1, per_page: int = 50):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    # Filter pagination
    total = len(projects)
    projects_paged = projects[(page - 1) * per_page : page * per_page]
    # Batch-load the latest snapshot per project to avoid N+1 queries.
    if projects_paged:
        from sqlalchemy import func

        latest = (
            db.query(
                RepositorySnapshot.project_id,
                func.max(RepositorySnapshot.created_at).label("latest_created"),
            )
            .filter(RepositorySnapshot.project_id.in_([p.id for p in projects_paged]))
            .group_by(RepositorySnapshot.project_id)
            .all()
        )
        latest_by_project = {pid: created for pid, created in latest}
        snapshots = {}
        for pid, created in latest_by_project.items():
            snap = (
                db.query(RepositorySnapshot)
                .filter(RepositorySnapshot.project_id == pid, RepositorySnapshot.created_at == created)
                .order_by(RepositorySnapshot.created_at.desc())
                .first()
            )
            if snap:
                snapshots[pid] = snap
    else:
        snapshots = {}
    return {
        "items": [
            ProjectOut(
                id=str(p.id),
                full_name=p.full_name,
                owner=p.owner,
                name=p.name,
                visibility=p.visibility,
                default_branch=p.default_branch,
                description=p.description,
                is_fixture=p.is_fixture,
                latest_snapshot=_snapshot_out(snapshots[p.id]).model_dump() if p.id in snapshots else None,
            )
            for p in projects_paged
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if per_page else 1,
    }


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    # Return with latest snapshot
    return _project_out(project, db)


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    db.delete(project)
    db.commit()
    return {"ok": True}


@router.post("/projects/{project_id}/analyses", response_model=AnalysisJobOut)
def queue_analysis(project_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    snapshot = RepositorySnapshot(
        project_id=project.id,
        commit_sha="",
        analyzer_version="dna-analyzer-1.0",
        score_model_version="dna-core-1.0",
        status="PENDING",
        limits_json={
            "max_files": settings.analysis_max_files,
            "max_commits": settings.analysis_max_commits,
            "max_bytes": settings.analysis_max_bytes,
        },
    )
    db.add(snapshot)
    db.flush()
    job = AnalysisJob(snapshot_id=snapshot.id, state="QUEUED")
    db.add(job)
    db.commit()
    return AnalysisJobOut(
        id=str(job.id),
        snapshot_id=str(snapshot.id),
        state="QUEUED",
        progress=0,
        phase="queued",
    )


@router.get("/analysis-jobs/{job_id}", response_model=AnalysisJobOut)
def get_job(job_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    job = db.get(AnalysisJob, parse_id(job_id, "job_id"))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return AnalysisJobOut(
        id=str(job.id),
        snapshot_id=str(job.snapshot_id),
        state=job.state,
        progress=job.progress,
        phase=job.phase,
        error_code=job.error_code,
        error_detail=_redact(job.error_detail),
        attempts=job.attempts,
    )


@router.post("/analysis-jobs/{job_id}/cancel")
def cancel_job(job_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    job = db.get(AnalysisJob, parse_id(job_id, "job_id"))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.state in ("QUEUED", "RETRY"):
        job.state = "CANCELLED"
        job.finished_at = None
        db.commit()
    return {"ok": True}


@router.get("/projects/{project_id}/snapshots", response_model=list[SnapshotOut])
def list_snapshots(project_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    snapshots = (
        db.query(RepositorySnapshot)
        .filter(RepositorySnapshot.project_id == project.id)
        .order_by(RepositorySnapshot.created_at.desc())
        .all()
    )
    return [_snapshot_out(s) for s in snapshots]


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotOut)
def get_snapshot(snapshot_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    snap = db.get(RepositorySnapshot, parse_id(snapshot_id, "snapshot_id"))
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return _snapshot_out(snap)


def _redact(text: str | None) -> str | None:
    """Trim error detail to avoid leaking sensitive internals to clients."""
    if not text:
        return text
    return text[:300]