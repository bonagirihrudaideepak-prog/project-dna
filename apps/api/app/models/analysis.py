from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_pk


class Artifact(Base, TimestampMixin):
    __tablename__ = "artifacts"

    id: Mapped[str] = uuid_pk()
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("repository_snapshots.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[str] = mapped_column(String(40), nullable=False)  # release, pr, issue, commit, tag
    provider_id: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    path: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    snapshot: Mapped["RepositorySnapshot"] = relationship(back_populates="artifacts")
    events: Mapped[list["EventArtifact"]] = relationship(
        back_populates="artifact", cascade="all, delete-orphan"
    )


class FileRecord(Base, TimestampMixin):
    __tablename__ = "files"

    id: Mapped[str] = uuid_pk()
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("repository_snapshots.id", ondelete="CASCADE"), index=True, nullable=False
    )
    path: Mapped[str] = mapped_column(String(2000), nullable=False)
    extension: Mapped[str | None] = mapped_column(String(20), nullable=True)
    language: Mapped[str | None] = mapped_column(String(60), nullable=True)
    bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_generated: Mapped[bool] = mapped_column(default=False, nullable=False)

    snapshot: Mapped["RepositorySnapshot"] = relationship(back_populates="files")


class FileChange(Base, TimestampMixin):
    __tablename__ = "file_changes"

    id: Mapped[str] = uuid_pk()
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("repository_snapshots.id", ondelete="CASCADE"), index=True, nullable=False
    )
    commit_artifact_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    file_path: Mapped[str] = mapped_column(String(2000), nullable=False)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), index=True, nullable=True)
    additions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deletions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    change_type: Mapped[str] = mapped_column(String(20), default="modified", nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class MetricValue(Base, TimestampMixin):
    __tablename__ = "metric_values"

    id: Mapped[str] = uuid_pk()
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("repository_snapshots.id", ondelete="CASCADE"), index=True, nullable=False
    )
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    raw_value_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    normalized_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    extractor_version: Mapped[str] = mapped_column(String(40), default="extractor-1.0", nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    snapshot: Mapped["RepositorySnapshot"] = relationship(back_populates="metric_values")
    score_evidence: Mapped[list["ScoreEvidence"]] = relationship(
        back_populates="metric_value", cascade="all, delete-orphan"
    )


class DNAScore(Base, TimestampMixin):
    __tablename__ = "dna_scores"

    id: Mapped[str] = uuid_pk()
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("repository_snapshots.id", ondelete="CASCADE"), index=True, nullable=False
    )
    dimension: Mapped[str] = mapped_column(String(40), nullable=False)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coverage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence: Mapped[str] = mapped_column(String(30), default="insufficient", nullable=False)
    direction: Mapped[str] = mapped_column(String(30), nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False)
    explanation_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    snapshot: Mapped["RepositorySnapshot"] = relationship(back_populates="dna_scores")
    evidence: Mapped[list["ScoreEvidence"]] = relationship(
        back_populates="score", cascade="all, delete-orphan"
    )


class ScoreEvidence(Base, TimestampMixin):
    __tablename__ = "score_evidence"

    id: Mapped[str] = uuid_pk()
    score_id: Mapped[str] = mapped_column(ForeignKey("dna_scores.id", ondelete="CASCADE"), index=True, nullable=False)
    metric_value_id: Mapped[str] = mapped_column(
        ForeignKey("metric_values.id", ondelete="CASCADE"), index=True, nullable=False
    )
    indicator_key: Mapped[str] = mapped_column(String(80), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    quality: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    contribution: Mapped[float | None] = mapped_column(Float, nullable=True)

    score: Mapped["DNAScore"] = relationship(back_populates="evidence")
    metric_value: Mapped["MetricValue"] = relationship(back_populates="score_evidence")
