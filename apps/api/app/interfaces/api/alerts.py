"""Trends and alerts endpoints for the DNA dashboard."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...adapters.cache_service import CacheService
from ...adapters.db import get_db
from ...config import settings
from ...models import Alert, AlertRule, DNAScore, Project, ProjectMembership, RepositorySnapshot
from ..deps import current_user, optional_user, parse_id
from ..schemas import AlertOut, AlertRuleIn, AlertRuleOut, TrendPoint
from .projects import require_membership

router = APIRouter(tags=["alerts"])

_cache_service = CacheService()

DIMENSIONS = {
    "technical_complexity",
    "maintainability",
    "testing_maturity",
    "documentation_quality",
    "evolution_health",
    "delivery_readiness",
    "scalability_readiness",
    "technical_debt_risk",
}


@router.get("/projects/{project_id}/trends", response_model=list[TrendPoint])
def get_trends(
    project_id: str,
    user_id: str | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    cache_key = f"trends:{project.id}"
    cached = _cache_service.get(cache_key)
    if cached is not None:
        return cached
    snapshots = (
        db.query(RepositorySnapshot)
        .filter(RepositorySnapshot.project_id == project.id)
        .order_by(RepositorySnapshot.created_at.asc())
        .all()
    )
    if not snapshots:
        return []
    ids = [s.id for s in snapshots]
    scores = (
        db.query(DNAScore)
        .filter(DNAScore.snapshot_id.in_(ids))
        .order_by(DNAScore.dimension)
        .all()
    )
    scores_by_snap: dict[str, dict[str, int | None]] = {}
    for sc in scores:
        # Withheld scores (coverage < 0.35) stay None -> rendered as gaps.
        scores_by_snap.setdefault(sc.snapshot_id, {})[sc.dimension] = (
            sc.score if sc.coverage >= 0.35 else None
        )
    payload = [
        TrendPoint(
            snapshot_id=str(s.id),
            captured_at=s.captured_at,
            created_at=s.created_at,
            scores=scores_by_snap.get(s.id, {}),
        ).model_dump(mode="json")
        for s in snapshots
    ]
    _cache_service.set(cache_key, payload, ttl=settings.cache_dna_ttl)
    return payload


@router.get("/projects/{project_id}/alerts", response_model=list[AlertRuleOut])
def list_rules(
    project_id: str,
    user_id: str | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    rules = db.query(AlertRule).filter(AlertRule.project_id == project.id).all()
    return rules


@router.post("/projects/{project_id}/alerts", response_model=AlertRuleOut, status_code=201)
def create_rule(
    project_id: str,
    body: AlertRuleIn,
    user_id: str = Depends(current_user),
    db: Session = Depends(get_db),
):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    if body.dimension not in DIMENSIONS:
        raise HTTPException(status_code=422, detail=f"Unknown dimension: {body.dimension}")
    existing = (
        db.query(AlertRule)
        .filter(AlertRule.project_id == project.id, AlertRule.dimension == body.dimension)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="A rule already exists for this dimension")
    rule = AlertRule(
        project_id=project.id,
        dimension=body.dimension,
        operator=body.operator,
        threshold=body.threshold,
        enabled=True,
        created_by=user_id,
    )
    db.add(rule)
    db.commit()
    _cache_service.invalidate_project(project.id)
    return rule


@router.patch("/projects/{project_id}/alerts/{rule_id}", response_model=AlertRuleOut)
def update_rule(
    project_id: str,
    rule_id: str,
    body: AlertRuleIn,
    user_id: str = Depends(current_user),
    db: Session = Depends(get_db),
):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    rule = db.get(AlertRule, parse_id(rule_id, "rule_id"))
    if not rule or rule.project_id != project.id:
        raise HTTPException(status_code=404, detail="Rule not found")
    if body.dimension not in DIMENSIONS:
        raise HTTPException(status_code=422, detail=f"Unknown dimension: {body.dimension}")
    rule.dimension = body.dimension
    rule.operator = body.operator
    rule.threshold = body.threshold
    db.commit()
    _cache_service.invalidate_project(project.id)
    return rule


@router.delete("/projects/{project_id}/alerts/{rule_id}")
def delete_rule(
    project_id: str,
    rule_id: str,
    user_id: str = Depends(current_user),
    db: Session = Depends(get_db),
):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    rule = db.get(AlertRule, parse_id(rule_id, "rule_id"))
    if not rule or rule.project_id != project.id:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    _cache_service.invalidate_project(project.id)
    return {"ok": True}


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    acknowledged: bool = Query(False, description="Include acknowledged alerts"),
    user_id: str | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    query = db.query(Alert).join(AlertRule).join(Project)
    if user_id:
        member_ids = [
            m.project_id
            for m in db.query(ProjectMembership).filter(ProjectMembership.user_id == user_id).all()
        ]
        if settings.env == "development":
            fixture_ids = [
                p.id for p in db.query(Project).filter(Project.is_fixture.is_(True)).all()
            ]
            query = query.filter(AlertRule.project_id.in_(set(member_ids) | set(fixture_ids)))
        else:
            query = query.filter(AlertRule.project_id.in_(member_ids))
    elif settings.env == "development":
        fixture_ids = [p.id for p in db.query(Project).filter(Project.is_fixture.is_(True)).all()]
        query = query.filter(AlertRule.project_id.in_(fixture_ids))
    else:
        query = query.filter(False)
    if not acknowledged:
        query = query.filter(Alert.acknowledged_at.is_(None))
    return query.order_by(Alert.fired_at.desc()).limit(200).all()


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    alert = db.get(Alert, parse_id(alert_id, "alert_id"))
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    require_membership(db, alert.rule.project_id, user_id)
    if alert.acknowledged_at is None:
        alert.acknowledged_at = datetime.now(timezone.utc)
        db.commit()
    return {"ok": True}