"""Projects, repositories, snapshots, and analysis jobs.

Thin HTTP layer: request parsing, auth dependency wiring, response models.
Business rules live in ``application/project_service``; errors raised there
are rendered by the global DNAError handler as the standard error envelope.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...adapters.db import get_db
from ...adapters.errors import NotFoundError
from ...adapters.github import GitHubAdapter
from ...application.project_service import (
    cache as _cache_service,
)
from ...application.project_service import (
    delete_project as delete_project_usecase,
)
from ...application.project_service import (
    import_project as import_project_usecase,
)
from ...application.project_service import (
    queue_analysis as queue_analysis_usecase,
)
from ...application.project_service import (
    resolve_project,
)
from ...config import settings
from ...config.constants import SNAPSHOTS_MAX_LIST
from ...models import AnalysisJob, Project, ProjectMembership, RepositorySnapshot
from ..deps import current_user, optional_user, parse_id
from ..schemas import AnalysisJobOut, GitHubRepoOut, ImportProjectIn, ProjectOut, SnapshotOut

router = APIRouter(tags=["projects"])


def require_membership(db: Session, project_id: str | uuid.UUID, user_id: str | None) -> Project:
    """Shared authorization resolver used by every project-scoped router.

    Accepts a UUID instance as well as a string: internal callers pass ORM
    attributes (e.g. ``snapshot.project_id``) directly."""
    pid = str(project_id) if isinstance(project_id, uuid.UUID) else parse_id(project_id, "project_id")
    return resolve_project(db, pid, user_id)


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


def _get_cache_service():
    return _cache_service


@router.get("/github/repositories", response_model=list[GitHubRepoOut])
async def list_repositories(
    q: str = "",
    page: int = 1,
    per_page: int = 30,
    user_id: str | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    """List accessible repositories. When no OAuth token is configured, list
    seeded fixture repositories for offline development.

    Authenticated in production: this route proxies through the server-level
    GitHub token, so anonymous access would leak token-scoped listings and burn
    the server's rate limit. Fixture fallback stays world-readable in dev."""
    if settings.env == "production" and not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
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
                except Exception:  # noqa: BLE001 - unreadable manifests are skipped
                    continue
    if not out:
        raise HTTPException(status_code=503, detail="No GitHub token and no fixtures available")
    return out


@router.post("/projects/import", response_model=ProjectOut)
def import_project(
    body: ImportProjectIn,
    user_id: str = Depends(current_user),
    db: Session = Depends(get_db),
):
    full_name = body.full_name.strip().lstrip("/")
    project = import_project_usecase(db, user_id, full_name, body.branch)
    return _project_out(project, db)


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    user_id: str | None = Depends(optional_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
):
    from sqlalchemy import func, tuple_

    query = db.query(Project).order_by(Project.created_at.desc())
    if user_id:
        member_ids = [m.project_id for m in db.query(ProjectMembership).filter(ProjectMembership.user_id == user_id).all()]
        if settings.env == "development":
            query = query.filter((Project.id.in_(member_ids)) | (Project.is_fixture.is_(True)))
        else:
            query = query.filter(Project.id.in_(member_ids))
    elif settings.env == "development":
        query = query.filter(Project.is_fixture.is_(True))
    else:
        # Production: unauthenticated access is already rejected by optional_user.
        query = query.filter(False)
    cache_key = f"projects:list:{user_id or 'anon'}:{page}:{per_page}"
    cached = _cache_service.get(cache_key)
    if cached is not None:
        return cached
    projects_paged = query.offset((page - 1) * per_page).limit(per_page).all()
    # Batch-load the latest snapshot per project in ONE extra query to avoid N+1.
    snapshots: dict = {}
    if projects_paged:
        latest_pairs = (
            db.query(
                RepositorySnapshot.project_id,
                func.max(RepositorySnapshot.created_at).label("latest_created"),
            )
            .filter(RepositorySnapshot.project_id.in_([p.id for p in projects_paged]))
            .group_by(RepositorySnapshot.project_id)
            .all()
        )
        if latest_pairs:
            rows = (
                db.query(RepositorySnapshot)
                .filter(
                    tuple_(RepositorySnapshot.project_id, RepositorySnapshot.created_at).in_(latest_pairs)
                )
                .order_by(RepositorySnapshot.created_at.desc())
                .all()
            )
            for snap in rows:
                # Ties on created_at resolve to the most recently loaded row.
                snapshots[snap.project_id] = snap
    payload = [
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
        ).model_dump(mode="json")
        for p in projects_paged
    ]
    _cache_service.set(cache_key, payload, ttl=settings.cache_list_ttl)
    return payload


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    cache_key = f"projects:item:{pid}"
    cached = _get_cache_service().get(cache_key)
    if cached is not None:
        return cached
    payload = _project_out(project, db).model_dump(mode="json")
    _get_cache_service().set(cache_key, payload, ttl=settings.cache_project_ttl)
    return payload


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    delete_project_usecase(db, project, user_id)
    return {"ok": True}


@router.post("/projects/{project_id}/analyses", response_model=AnalysisJobOut)
def queue_analysis(project_id: str, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    job = queue_analysis_usecase(db, project)
    return AnalysisJobOut(
        id=str(job.id),
        snapshot_id=str(job.snapshot_id),
        state="QUEUED",
        progress=0,
        phase="queued",
    )


@router.get("/analysis-jobs/{job_id}", response_model=AnalysisJobOut)
def get_job(job_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    job = db.get(AnalysisJob, parse_id(job_id, "job_id"))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    snapshot = db.get(RepositorySnapshot, job.snapshot_id)
    if snapshot:
        require_membership(db, snapshot.project_id, user_id)
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
def cancel_job(job_id: str, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    job = db.get(AnalysisJob, parse_id(job_id, "job_id"))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    snapshot = db.get(RepositorySnapshot, job.snapshot_id)
    if snapshot:
        require_membership(db, snapshot.project_id, user_id)
    if job.state in ("QUEUED", "RETRY"):
        job.state = "CANCELLED"
        job.finished_at = None
        db.commit()
    return {"ok": True}


@router.get("/projects/{project_id}/snapshots", response_model=list[SnapshotOut])
def list_snapshots(project_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    cache_key = f"snapshots:list:{project.id}"
    cached = _get_cache_service().get(cache_key)
    if cached is not None:
        return cached
    snapshots = (
        db.query(RepositorySnapshot)
        .filter(RepositorySnapshot.project_id == project.id)
        .order_by(RepositorySnapshot.created_at.desc())
        .limit(SNAPSHOTS_MAX_LIST)
        .all()
    )
    payload = [_snapshot_out(s).model_dump(mode="json") for s in snapshots]
    _get_cache_service().set(cache_key, payload, ttl=settings.cache_list_ttl)
    return payload


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotOut)
def get_snapshot(snapshot_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    snap = db.get(RepositorySnapshot, parse_id(snapshot_id, "snapshot_id"))
    if not snap:
        raise NotFoundError("Snapshot not found")
    require_membership(db, snap.project_id, user_id)
    return _snapshot_out(snap)


def _redact(text: str | None) -> str | None:
    """Trim error detail to avoid leaking sensitive internals to clients."""
    if not text:
        return text
    return text[:300]
