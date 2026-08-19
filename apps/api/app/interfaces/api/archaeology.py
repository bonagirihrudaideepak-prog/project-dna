"""Decision Archaeology and failed experiments endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...adapters.db import get_db
from ...models import (
    Decision,
    DecisionAlternative,
    DecisionLink,
    Experiment,
    OutcomeReview,
)
from ..deps import current_user, optional_user, parse_id
from ..schemas import (
    DecisionIn,
    DecisionOut,
    DecisionPatchIn,
    ExperimentIn,
    ExperimentOut,
    ExperimentPatchIn,
    OutcomeReviewIn,
)
from .projects import require_membership

router = APIRouter(tags=["archaeology"])


def _resolve_decision(db: Session, decision_id: str, user_id: str) -> Decision:
    """Load a decision and enforce membership on its owning project."""
    d = db.get(Decision, parse_id(decision_id, "decision_id"))
    if not d:
        raise HTTPException(status_code=404, detail="Decision not found")
    require_membership(db, d.project_id, user_id)
    return d


def _resolve_experiment(db: Session, experiment_id: str, user_id: str) -> Experiment:
    """Load an experiment and enforce membership on its owning project."""
    e = db.get(Experiment, parse_id(experiment_id, "experiment_id"))
    if not e:
        raise HTTPException(status_code=404, detail="Experiment not found")
    require_membership(db, e.project_id, user_id)
    return e


@router.get("/projects/{project_id}/decisions")
def list_decisions(project_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    from sqlalchemy.orm import selectinload

    project = require_membership(db, parse_id(project_id, "project_id"), user_id)
    rows = (
        db.query(Decision)
        .options(selectinload(Decision.alternatives), selectinload(Decision.links), selectinload(Decision.outcome_reviews))
        .filter(Decision.project_id == project.id, Decision.archived.is_(False))
        .order_by(Decision.created_at.desc())
        .all()
    )
    return [DecisionOut.model_validate(d) for d in rows]


@router.post("/projects/{project_id}/decisions")
def create_decision(project_id: str, body: DecisionIn, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    project = require_membership(db, parse_id(project_id, "project_id"), user_id)
    d = Decision(
        project_id=project.id,
        title=body.title,
        context=body.context,
        decision_text=body.decision_text,
        reason=body.reason,
        expected_impact=body.expected_impact,
        status=body.status,
        decided_at=body.decided_at,
        provenance="user",
    )
    db.add(d)
    db.flush()
    for alt in body.alternatives:
        db.add(DecisionAlternative(decision_id=d.id, **{k: v for k, v in alt.items() if k in ("name", "advantages", "disadvantages", "rejection_reason")}))
    for link in body.links:
        db.add(DecisionLink(decision_id=d.id, **{k: v for k, v in link.items() if k in ("entity_type", "entity_id", "relation")}))
    db.commit()
    return DecisionOut.model_validate(d)


@router.get("/decisions/{decision_id}")
def get_decision(decision_id: str, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    d = _resolve_decision(db, decision_id, user_id)
    return DecisionOut.model_validate(d)


@router.patch("/decisions/{decision_id}")
def update_decision(decision_id: str, body: DecisionPatchIn, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    d = _resolve_decision(db, decision_id, user_id)
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(d, field, value)
    db.commit()
    return DecisionOut.model_validate(d)


@router.post("/decisions/{decision_id}/outcome-reviews")
def add_outcome_review(decision_id: str, body: OutcomeReviewIn, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    d = _resolve_decision(db, decision_id, user_id)
    r = OutcomeReview(
        decision_id=d.id,
        reviewed_at=body.reviewed_at,
        actual_impact=body.actual_impact,
        evidence=body.evidence,
        verdict=body.verdict,
    )
    db.add(r)
    d.status = "reviewed"
    db.commit()
    return DecisionOut.model_validate(d)


@router.get("/projects/{project_id}/experiments")
def list_experiments(project_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    project = require_membership(db, parse_id(project_id, "project_id"), user_id)
    rows = (
        db.query(Experiment)
        .filter(Experiment.project_id == project.id, Experiment.archived.is_(False))
        .order_by(Experiment.created_at.desc())
        .all()
    )
    return [ExperimentOut.model_validate(e) for e in rows]


@router.post("/projects/{project_id}/experiments")
def create_experiment(project_id: str, body: ExperimentIn, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    project = require_membership(db, parse_id(project_id, "project_id"), user_id)
    e = Experiment(
        project_id=project.id,
        title=body.title,
        hypothesis=body.hypothesis,
        success_criterion=body.success_criterion,
        method=body.method,
        result=body.result,
        decision=body.decision,
        reason=body.reason,
        start_at=body.start_at,
        evaluated_at=body.evaluated_at,
    )
    db.add(e)
    db.commit()
    return ExperimentOut.model_validate(e)


@router.patch("/experiments/{experiment_id}")
def update_experiment(experiment_id: str, body: ExperimentPatchIn, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    e = _resolve_experiment(db, experiment_id, user_id)
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(e, field, value)
    db.commit()
    return ExperimentOut.model_validate(e)