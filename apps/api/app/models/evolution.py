from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_pk


class TimelineEvent(Base, TimestampMixin):
    __tablename__ = "timeline_events"

    id: Mapped[str] = uuid_pk()
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("repository_snapshots.id", ondelete="CASCADE"), index=True, nullable=False
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(2000), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[float] = mapped_column(default=1.0, nullable=False)
    provenance: Mapped[str] = mapped_column(String(30), default="observed", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    snapshot: Mapped["RepositorySnapshot"] = relationship(back_populates="timeline_events")
    artifacts: Mapped[list["EventArtifact"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class EventArtifact(Base, TimestampMixin):
    __tablename__ = "event_artifacts"

    id: Mapped[str] = uuid_pk()
    event_id: Mapped[str] = mapped_column(ForeignKey("timeline_events.id", ondelete="CASCADE"), index=True, nullable=False)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), index=True, nullable=False)
    relation: Mapped[str] = mapped_column(String(30), default="source", nullable=False)

    event: Mapped["TimelineEvent"] = relationship(back_populates="artifacts")
    artifact: Mapped["Artifact"] = relationship(back_populates="events")


class Component(Base, TimestampMixin):
    __tablename__ = "components"

    id: Mapped[str] = uuid_pk()
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    path_rules_json: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)


class EventComponent(Base, TimestampMixin):
    __tablename__ = "event_components"

    id: Mapped[str] = uuid_pk()
    event_id: Mapped[str] = mapped_column(ForeignKey("timeline_events.id", ondelete="CASCADE"), index=True, nullable=False)
    component_id: Mapped[str] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"), index=True, nullable=False)
    impact_type: Mapped[str] = mapped_column(String(30), default="affected", nullable=False)


class Decision(Base, TimestampMixin):
    __tablename__ = "decisions"

    id: Mapped[str] = uuid_pk()
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_impact: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="proposed", nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    author_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    provenance: Mapped[str] = mapped_column(String(30), default="user", nullable=False)
    outcome_review_due: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    archived: Mapped[bool] = mapped_column(default=False, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="decisions")
    alternatives: Mapped[list["DecisionAlternative"]] = relationship(
        back_populates="decision", cascade="all, delete-orphan"
    )
    outcome_reviews: Mapped[list["OutcomeReview"]] = relationship(
        back_populates="decision", cascade="all, delete-orphan"
    )
    links: Mapped[list["DecisionLink"]] = relationship(
        back_populates="decision", cascade="all, delete-orphan"
    )


class DecisionAlternative(Base, TimestampMixin):
    __tablename__ = "decision_alternatives"

    id: Mapped[str] = uuid_pk()
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    advantages: Mapped[str | None] = mapped_column(Text, nullable=True)
    disadvantages: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    decision: Mapped["Decision"] = relationship(back_populates="alternatives")


class DecisionLink(Base, TimestampMixin):
    __tablename__ = "decision_links"

    id: Mapped[str] = uuid_pk()
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    relation: Mapped[str] = mapped_column(String(30), default="related", nullable=False)

    decision: Mapped["Decision"] = relationship(back_populates="links")


class OutcomeReview(Base, TimestampMixin):
    __tablename__ = "outcome_reviews"

    id: Mapped[str] = uuid_pk()
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    verdict: Mapped[str] = mapped_column(String(40), default="neutral", nullable=False)
    author_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)

    decision: Mapped["Decision"] = relationship(back_populates="outcome_reviews")


class Experiment(Base, TimestampMixin):
    __tablename__ = "experiments"

    id: Mapped[str] = uuid_pk()
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    success_criterion: Mapped[str | None] = mapped_column(Text, nullable=True)
    method: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str] = mapped_column(String(40), default="inconclusive", nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    archived: Mapped[bool] = mapped_column(default=False, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="experiments")
    links: Mapped[list["ExperimentLink"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )


class ExperimentLink(Base, TimestampMixin):
    __tablename__ = "experiment_links"

    id: Mapped[str] = uuid_pk()
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    relation: Mapped[str] = mapped_column(String(30), default="related", nullable=False)

    experiment: Mapped["Experiment"] = relationship(back_populates="links")
