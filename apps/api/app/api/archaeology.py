"""Decision Archaeology and failed experiments endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import optional_user, parse_id
from ..models import (
    Decision,
    DecisionAlternative,
    DecisionLink,
    Experiment,
    ExperimentLink,
    OutcomeReview,
    Project,
)
from ..schemas import DecisionIn, DecisionPatchIn, ExperimentIn, ExperimentPatchIn, OutcomeReviewIn

router = APIRouter(tags=["archaeology"])


def _get_project(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _decision_out(d: Decision) -> dict:
    return {
        "id": str(d.id),
        "project_id": str(d.project_id),
        "title": d.title,
        "context": d.context,
        "decision_text": d.decision_text,
        "reason": d.reason,
        "expected_impact": d.expected_impact or {},
        "status": d.status,
        "decided_at": d.decided_at,
        "provenance": d.provenance,
        "outcome_review_due": d.outcome_review_due,
        "archived": d.archived,
        "alternatives": [
            {
                "id": str(a.id),
                "name": a.name,
                "advantages": a.advantages,
                "disadvantages": a.disadvantages,
                "rejection_reason": a.rejection_reason,
            }
            for a in d.alternatives
        ],
        "links": [{"id": str(l.id), "entity_type": l.entity_type, "entity_id": l.entity_id, "relation": l.relation} for l in d.links],
        "outcome_reviews": [
            {
                "id": str(r.id),
                "reviewed_at": r.reviewed_at,
                "actual_impact": r.actual_impact,
                "evidence": r.evidence,
                "verdict": r.verdict,
            }
            for r in d.outcome_reviews
        ],
    }


@router.get("/projects/{project_id}/decisions")
def list_decisions(project_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    from sqlalchemy.orm import selectinload

    project = _get_project(db, parse_id(project_id, "project_id"))
    rows = (
        db.query(Decision)
        .options(selectinload(Decision.alternatives), selectinload(Decision.links), selectinload(Decision.outcome_reviews))
        .filter(Decision.project_id == project.id, Decision.archived.is_(False))
        .order_by(Decision.created_at.desc())
        .all()
    )
    return [_decision_out(d) for d in rows]


@router.post("/projects/{project_id}/decisions")
def create_decision(project_id: str, body: DecisionIn, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    project = _get_project(db, parse_id(project_id, "project_id"))
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
    return _decision_out(d)


@router.get("/decisions/{decision_id}")
def get_decision(decision_id: str, db: Session = Depends(get_db)):
    d = db.get(Decision, decision_id)
    if not d:
        raise HTTPException(status_code=404, detail="Decision not found")
    return _decision_out(d)


@router.patch("/decisions/{decision_id}")
def update_decision(decision_id: str, body: DecisionPatchIn, db: Session = Depends(get_db)):
    d = db.get(Decision, decision_id)
    if not d:
        raise HTTPException(status_code=404, detail="Decision not found")
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(d, field, value)
    db.commit()
    return _decision_out(d)


@router.post("/decisions/{decision_id}/outcome-reviews")
def add_outcome_review(decision_id: str, body: OutcomeReviewIn, db: Session = Depends(get_db)):
    d = db.get(Decision, decision_id)
    if not d:
        raise HTTPException(status_code=404, detail="Decision not found")
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
    return _decision_out(d)


@router.get("/projects/{project_id}/experiments")
def list_experiments(project_id: str, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    project = _get_project(db, parse_id(project_id, "project_id"))
    rows = (
        db.query(Experiment)
        .filter(Experiment.project_id == project.id, Experiment.archived.is_(False))
        .order_by(Experiment.created_at.desc())
        .all()
    )
    return [_experiment_out(e) for e in rows]


@router.post("/projects/{project_id}/experiments")
def create_experiment(project_id: str, body: ExperimentIn, user_id: str | None = Depends(optional_user), db: Session = Depends(get_db)):
    project = _get_project(db, parse_id(project_id, "project_id"))
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
    return _experiment_out(e)


def _experiment_out(e: Experiment) -> dict:
    return {
        "id": str(e.id),
        "project_id": str(e.project_id),
        "title": e.title,
        "hypothesis": e.hypothesis,
        "success_criterion": e.success_criterion,
        "method": e.method,
        "result": e.result,
        "decision": e.decision,
        "reason": e.reason,
        "start_at": e.start_at,
        "evaluated_at": e.evaluated_at,
        "archived": e.archived,
    }


@router.patch("/experiments/{experiment_id}")
def update_experiment(experiment_id: str, body: ExperimentPatchIn, db: Session = Depends(get_db)):
    e = db.get(Experiment, experiment_id)
    if not e:
        raise HTTPException(status_code=404, detail="Experiment not found")
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(e, field, value)
    db.commit()
    return _experiment_out(e)