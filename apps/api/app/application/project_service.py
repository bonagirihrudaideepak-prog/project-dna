"""Project and snapshot use-cases.

Owns the business rules for importing projects, queuing analyses, and
deleting projects. Routers stay thin: parse HTTP input, call a use-case,
serialize the returned ORM objects. Use-cases raise ``DNAError`` subclasses
(adapters/errors) which the API layer renders as the standard error envelope.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from ..adapters.cache_service import CacheService
from ..adapters.errors import NotFoundError, PermissionDeniedError, ValidationError
from ..config import settings
from ..models import AnalysisJob, Project, ProjectMembership, RepositorySnapshot

_cache_service = CacheService()
cache = _cache_service  # public alias for routers that share the same instance


def resolve_project(db: Session, project_id: str, user_id: str | None) -> Project:
    """Return the project when ``user_id`` may access it.

    Fixture demo projects remain world-readable outside production so the
    offline dev flow works without OAuth."""
    project = db.get(Project, project_id)
    if not project:
        raise NotFoundError("Project not found")
    if user_id:
        member = (
            db.query(ProjectMembership)
            .filter_by(project_id=project.id, user_id=user_id)
            .first()
        )
        if not member:
            if project.is_fixture and settings.env == "development":
                return project
            raise PermissionDeniedError("Not a member of this project")
    elif settings.env == "production":
        raise PermissionDeniedError("Authentication required")
    return project


def _fixture_dir_for(full_name: str) -> Path | None:
    fixture_root = Path(settings.fixture_root)
    if not fixture_root.exists():
        return None
    for d in sorted(fixture_root.iterdir()):
        manifest = d / "manifest.json"
        if manifest.exists():
            try:
                if json.loads(manifest.read_text()).get("full_name") == full_name:
                    return d
            except Exception:  # noqa: BLE001 - unreadable manifest = not this fixture
                continue
    return None


def is_fixture(full_name: str) -> bool:
    return _fixture_dir_for(full_name) is not None


def import_project(db: Session, user_id: str, full_name: str, branch: str | None) -> Project:
    """Import an owner/repo reference, or join an existing project as member."""
    parts = full_name.split("/")
    if len(parts) != 2:
        raise ValidationError("Expected owner/repo")

    existing = db.query(Project).filter(Project.full_name == full_name).first()
    if existing:
        membership = (
            db.query(ProjectMembership)
            .filter_by(project_id=existing.id, user_id=user_id)
            .first()
        )
        if not membership:
            db.add(ProjectMembership(project_id=existing.id, user_id=user_id, role="member"))
            db.commit()
        _cache_service.invalidate_project(existing.id)
        return existing

    project = Project(
        full_name=full_name,
        owner=parts[0],
        name=parts[1],
        default_branch=branch or "main",
        visibility="public",
        is_fixture=is_fixture(full_name),
    )
    db.add(project)
    db.flush()
    db.add(ProjectMembership(project_id=project.id, user_id=user_id, role="owner"))
    db.commit()
    _cache_service.invalidate_project(project.id)
    return project


def queue_analysis(db: Session, project: Project) -> AnalysisJob:
    """Create a PENDING snapshot plus its QUEUED analysis job."""
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
    _cache_service.invalidate_project(project.id)
    return job


def delete_project(db: Session, project: Project, user_id: str) -> None:
    """Hard-delete a project (cascades snapshots/jobs/alerts). Owners only.

    Dev-mode fixture world-readability grants read access only."""
    membership = (
        db.query(ProjectMembership)
        .filter_by(project_id=project.id, user_id=user_id)
        .first()
    )
    if membership is None or membership.role != "owner":
        raise PermissionDeniedError("Only project owners can delete a project")
    db.delete(project)
    db.commit()
    _cache_service.invalidate_project(project.id)
