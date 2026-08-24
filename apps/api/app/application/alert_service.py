"""Alert rule and alert use-cases.

Business rules for creating, updating, deleting, and acknowledging alerts,
including the visibility rules for the cross-project alert inbox.
Routers stay thin and raise nothing but HTTP plumbing errors.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..adapters.cache_service import CacheService
from ..adapters.errors import ConflictError, NotFoundError, ValidationError
from ..config import settings
from ..config.constants import ALERTS_INBOX_MAX, DIMENSION_ORDER
from ..models import Alert, AlertRule, Project, ProjectMembership

_cache_service = CacheService()

KNOWN_DIMENSIONS = set(DIMENSION_ORDER)


def list_rules(db: Session, project: Project) -> list[AlertRule]:
    return db.query(AlertRule).filter(AlertRule.project_id == project.id).all()


def _validate_dimension(dimension: str) -> None:
    if dimension not in KNOWN_DIMENSIONS:
        raise ValidationError(f"Unknown dimension: {dimension}")


def create_rule(
    db: Session,
    project: Project,
    user_id: str,
    dimension: str,
    operator: str,
    threshold: int,
) -> AlertRule:
    _validate_dimension(dimension)
    existing = (
        db.query(AlertRule)
        .filter(AlertRule.project_id == project.id, AlertRule.dimension == dimension)
        .first()
    )
    if existing:
        raise ConflictError("A rule already exists for this dimension")
    rule = AlertRule(
        project_id=project.id,
        dimension=dimension,
        operator=operator,
        threshold=threshold,
        enabled=True,
        created_by=user_id,
    )
    db.add(rule)
    db.commit()
    _cache_service.invalidate_project(project.id)
    return rule


def update_rule(
    db: Session,
    project: Project,
    rule_id: str,
    dimension: str,
    operator: str,
    threshold: int,
) -> AlertRule:
    _validate_dimension(dimension)
    rule = db.get(AlertRule, rule_id)
    if not rule or rule.project_id != project.id:
        raise NotFoundError("Rule not found")
    rule.dimension = dimension
    rule.operator = operator
    rule.threshold = threshold
    db.commit()
    _cache_service.invalidate_project(project.id)
    return rule


def delete_rule(db: Session, project: Project, rule_id: str) -> None:
    rule = db.get(AlertRule, rule_id)
    if not rule or rule.project_id != project.id:
        raise NotFoundError("Rule not found")
    db.delete(rule)
    db.commit()
    _cache_service.invalidate_project(project.id)


def visible_project_ids(db: Session, user_id: str | None) -> set[str]:
    """Project ids whose alerts the caller may see.

    Mirrors the projects listing posture: members see their projects, dev mode
    additionally exposes fixture projects, and production denies anonymous
    access entirely."""
    if not user_id:
        if settings.env != "development":
            return set()
        return {
            p.id
            for p in db.query(Project).filter(Project.is_fixture.is_(True)).all()
        }
    member_ids = {
        m.project_id
        for m in db.query(ProjectMembership).filter(ProjectMembership.user_id == user_id).all()
    }
    if settings.env == "development":
        member_ids |= {
            p.id
            for p in db.query(Project).filter(Project.is_fixture.is_(True)).all()
        }
    return member_ids


def list_alerts(
    db: Session,
    user_id: str | None,
    acknowledged: bool = False,
) -> list[Alert]:
    query = db.query(Alert).join(AlertRule).join(Project)
    project_ids = visible_project_ids(db, user_id)
    query = query.filter(AlertRule.project_id.in_(project_ids))
    if not acknowledged:
        query = query.filter(Alert.acknowledged_at.is_(None))
    return query.order_by(Alert.fired_at.desc()).limit(ALERTS_INBOX_MAX).all()


def acknowledge_alert(db: Session, alert_id: str, user_id: str) -> None:
    from .project_service import resolve_project

    alert = db.get(Alert, alert_id)
    if not alert:
        raise NotFoundError("Alert not found")
    resolve_project(db, str(alert.rule.project_id), user_id)
    if alert.acknowledged_at is None:
        alert.acknowledged_at = datetime.now(timezone.utc)
        db.commit()
