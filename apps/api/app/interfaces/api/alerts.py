"""Trends and alerts endpoints for the DNA dashboard.

Thin HTTP layer over ``application/alert_service``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...adapters.db import get_db
from ...application.alert_service import (
    acknowledge_alert as acknowledge_usecase,
)
from ...application.alert_service import (
    create_rule as create_rule_usecase,
)
from ...application.alert_service import (
    delete_rule as delete_rule_usecase,
)
from ...application.alert_service import (
    list_alerts as list_alerts_usecase,
)
from ...application.alert_service import (
    list_rules as list_rules_usecase,
)
from ...application.alert_service import (
    update_rule as update_rule_usecase,
)
from ...config import settings
from ...config.constants import COVERAGE_INSUFFICIENT, TRENDS_MAX_SNAPSHOTS
from ...models import DNAScore, RepositorySnapshot
from ..deps import current_user, optional_user, parse_id
from ..schemas import AlertOut, AlertRuleIn, AlertRuleOut, TrendPoint
from .projects import require_membership

router = APIRouter(tags=["alerts"])


@router.get("/projects/{project_id}/trends", response_model=list[TrendPoint])
def get_trends(
    project_id: str,
    user_id: str | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    from ...adapters.cache_service import CacheService

    cache_service = CacheService()
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    cache_key = f"trends:{project.id}"
    cached = cache_service.get(cache_key)
    if cached is not None:
        return cached
    # Bounded window + scalar columns only: trends is a chart feed, and
    # loading every snapshot's full row (incl. JSONB) does not scale.
    snapshots = (
        db.query(
            RepositorySnapshot.id,
            RepositorySnapshot.captured_at,
            RepositorySnapshot.created_at,
        )
        .filter(RepositorySnapshot.project_id == project.id)
        .order_by(RepositorySnapshot.created_at.desc())
        .limit(TRENDS_MAX_SNAPSHOTS)
        .all()
    )
    if not snapshots:
        return []
    snapshots.reverse()  # oldest first for the chart
    ids = [s.id for s in snapshots]
    scores = (
        db.query(DNAScore.snapshot_id, DNAScore.dimension, DNAScore.score, DNAScore.coverage)
        .filter(DNAScore.snapshot_id.in_(ids))
        .all()
    )
    scores_by_snap: dict[str, dict[str, int | None]] = {}
    for snapshot_id, dimension, score, coverage in scores:
        # Withheld scores (coverage < 0.35) stay None -> rendered as gaps.
        scores_by_snap.setdefault(snapshot_id, {})[dimension] = (
            score if coverage >= COVERAGE_INSUFFICIENT else None
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
    cache_service.set(cache_key, payload, ttl=settings.cache_dna_ttl)
    return payload


@router.get("/projects/{project_id}/alerts", response_model=list[AlertRuleOut])
def list_rules(
    project_id: str,
    user_id: str | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    return list_rules_usecase(db, project)


@router.post("/projects/{project_id}/alerts", response_model=AlertRuleOut, status_code=201)
def create_rule(
    project_id: str,
    body: AlertRuleIn,
    user_id: str = Depends(current_user),
    db: Session = Depends(get_db),
):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    return create_rule_usecase(db, project, user_id, body.dimension, body.operator, body.threshold)


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
    return update_rule_usecase(
        db, project, parse_id(rule_id, "rule_id"), body.dimension, body.operator, body.threshold
    )


@router.delete("/projects/{project_id}/alerts/{rule_id}")
def delete_rule(
    project_id: str,
    rule_id: str,
    user_id: str = Depends(current_user),
    db: Session = Depends(get_db),
):
    pid = parse_id(project_id, "project_id")
    project = require_membership(db, pid, user_id)
    delete_rule_usecase(db, project, parse_id(rule_id, "rule_id"))
    return {"ok": True}


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    acknowledged: bool = Query(False, description="Include acknowledged alerts"),
    user_id: str | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    return list_alerts_usecase(db, user_id, acknowledged)


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    acknowledge_usecase(db, parse_id(alert_id, "alert_id"), user_id)
    return {"ok": True}
