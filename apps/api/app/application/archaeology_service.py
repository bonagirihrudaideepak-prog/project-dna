"""Decision archaeology use-cases: decisions, alternatives/links, outcome
reviews, and experiments. Membership enforcement reuses the project resolver.
Routers keep request parsing and response serialization."""

from __future__ import annotations

from sqlalchemy.orm import Session, selectinload

from ..adapters.errors import NotFoundError
from ..models import (
    Decision,
    DecisionAlternative,
    DecisionLink,
    Experiment,
    OutcomeReview,
)
from .project_service import resolve_project

_DECISION_ALT_FIELDS = ("name", "advantages", "disadvantages", "rejection_reason")
_DECISION_LINK_FIELDS = ("entity_type", "entity_id", "relation")
_EXPERIMENT_FIELDS = (
    "title",
    "hypothesis",
    "success_criterion",
    "method",
    "result",
    "decision",
    "reason",
    "start_at",
    "evaluated_at",
)


def list_decisions(db: Session, project_id: str) -> list[Decision]:
    return (
        db.query(Decision)
        .options(
            selectinload(Decision.alternatives),
            selectinload(Decision.links),
            selectinload(Decision.outcome_reviews),
        )
        .filter(Decision.project_id == project_id, Decision.archived.is_(False))
        .order_by(Decision.created_at.desc())
        .all()
    )


def create_decision(db: Session, project_id: str, **fields) -> Decision:
    d = Decision(project_id=project_id, provenance="user", **{k: v for k, v in fields.items() if k in _DECISION_FIELD_NAMES})
    db.add(d)
    db.flush()
    for alt in fields.get("alternatives") or ():
        db.add(DecisionAlternative(decision_id=d.id, **{k: v for k, v in alt.items() if k in _DECISION_ALT_FIELDS}))
    for link in fields.get("links") or ():
        db.add(DecisionLink(decision_id=d.id, **{k: v for k, v in link.items() if k in _DECISION_LINK_FIELDS}))
    db.commit()
    return d


_DECISION_FIELD_NAMES = (
    "title",
    "context",
    "decision_text",
    "reason",
    "expected_impact",
    "status",
    "decided_at",
)


def resolve_decision(db: Session, decision_id: str, user_id: str) -> Decision:
    d = db.get(Decision, decision_id)
    if not d:
        raise NotFoundError("Decision not found")
    resolve_project(db, str(d.project_id), user_id)
    return d


def update_instance(instance, updates: dict) -> None:
    """Apply a partial update payload (already schema-filtered) to an ORM row."""
    for field, value in updates.items():
        setattr(instance, field, value)


def add_outcome_review(
    db: Session,
    decision: Decision,
    *,
    reviewed_at,
    actual_impact=None,
    evidence=None,
    verdict: str,
) -> OutcomeReview:
    review = OutcomeReview(
        decision_id=decision.id,
        reviewed_at=reviewed_at,
        actual_impact=actual_impact,
        evidence=evidence,
        verdict=verdict,
    )
    db.add(review)
    decision.status = "reviewed"
    db.commit()
    return review


def list_experiments(db: Session, project_id: str) -> list[Experiment]:
    return (
        db.query(Experiment)
        .filter(Experiment.project_id == project_id, Experiment.archived.is_(False))
        .order_by(Experiment.created_at.desc())
        .all()
    )


def create_experiment(db: Session, project_id: str, **fields) -> Experiment:
    e = Experiment(project_id=project_id, **{k: v for k, v in fields.items() if k in _EXPERIMENT_FIELDS})
    db.add(e)
    db.commit()
    return e


def resolve_experiment(db: Session, experiment_id: str, user_id: str) -> Experiment:
    e = db.get(Experiment, experiment_id)
    if not e:
        raise NotFoundError("Experiment not found")
    resolve_project(db, str(e.project_id), user_id)
    return e
