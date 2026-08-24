"""Decision Archaeology and failed experiments endpoints.

Thin HTTP layer over ``application/archaeology_service``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...adapters.db import get_db
from ...application.archaeology_service import (
    add_outcome_review as add_outcome_review_usecase,
)
from ...application.archaeology_service import (
    create_decision as create_decision_usecase,
)
from ...application.archaeology_service import (
    create_experiment as create_experiment_usecase,
)
from ...application.archaeology_service import (
    list_decisions as list_decisions_usecase,
)
from ...application.archaeology_service import (
    list_experiments as list_experiments_usecase,
)
from ...application.archaeology_service import (
    resolve_decision,
    resolve_experiment,
    update_instance,
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


@router.get("/projects/{project_id}/decisions")
def list_decisions(project_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    project = require_membership(db, parse_id(project_id, "project_id"), user_id)
    return [DecisionOut.model_validate(d) for d in list_decisions_usecase(db, project.id)]


@router.post("/projects/{project_id}/decisions")
def create_decision(project_id: str, body: DecisionIn, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    project = require_membership(db, parse_id(project_id, "project_id"), user_id)
    d = create_decision_usecase(
        db,
        project.id,
        title=body.title,
        context=body.context,
        decision_text=body.decision_text,
        reason=body.reason,
        expected_impact=body.expected_impact,
        status=body.status,
        decided_at=body.decided_at,
        alternatives=list(body.alternatives),
        links=list(body.links),
    )
    return DecisionOut.model_validate(d)


@router.get("/decisions/{decision_id}")
def get_decision(decision_id: str, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    d = resolve_decision(db, parse_id(decision_id, "decision_id"), user_id)
    return DecisionOut.model_validate(d)


@router.patch("/decisions/{decision_id}")
def update_decision(decision_id: str, body: DecisionPatchIn, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    d = resolve_decision(db, parse_id(decision_id, "decision_id"), user_id)
    update_instance(d, body.model_dump(exclude_unset=True))
    db.commit()
    return DecisionOut.model_validate(d)


@router.post("/decisions/{decision_id}/outcome-reviews")
def add_outcome_review(decision_id: str, body: OutcomeReviewIn, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    d = resolve_decision(db, parse_id(decision_id, "decision_id"), user_id)
    add_outcome_review_usecase(
        db,
        d,
        reviewed_at=body.reviewed_at,
        actual_impact=body.actual_impact,
        evidence=body.evidence,
        verdict=body.verdict,
    )
    return DecisionOut.model_validate(d)


@router.get("/projects/{project_id}/experiments")
def list_experiments(project_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    project = require_membership(db, parse_id(project_id, "project_id"), user_id)
    return [ExperimentOut.model_validate(e) for e in list_experiments_usecase(db, project.id)]


@router.post("/projects/{project_id}/experiments")
def create_experiment(project_id: str, body: ExperimentIn, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    project = require_membership(db, parse_id(project_id, "project_id"), user_id)
    e = create_experiment_usecase(
        db,
        project.id,
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
    return ExperimentOut.model_validate(e)


@router.patch("/experiments/{experiment_id}")
def update_experiment(experiment_id: str, body: ExperimentPatchIn, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    e = resolve_experiment(db, parse_id(experiment_id, "experiment_id"), user_id)
    update_instance(e, body.model_dump(exclude_unset=True))
    db.commit()
    return ExperimentOut.model_validate(e)
