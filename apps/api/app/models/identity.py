from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, StringPKMixin, TimestampMixin, uuid_pk


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = uuid_pk()
    github_user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    login: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    connections: Mapped[list["GitHubConnection"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    memberships: Mapped[list["ProjectMembership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class GitHubConnection(Base, TimestampMixin):
    __tablename__ = "github_connections"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    # Fernet-encrypted OAuth token; plaintext never persisted
    encrypted_token: Mapped[bytes] = mapped_column(nullable=False)
    scopes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    token_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="connections")


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = uuid_pk()
    github_repo_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner: Mapped[str] = mapped_column(String(160), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    full_name: Mapped[str] = mapped_column(String(320), nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), default="public", nullable=False)
    default_branch: Mapped[str] = mapped_column(String(160), default="main", nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    is_fixture: Mapped[bool] = mapped_column(default=False, nullable=False)

    memberships: Mapped[list["ProjectMembership"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list["RepositorySnapshot"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    decisions: Mapped[list["Decision"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    experiments: Mapped[list["Experiment"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectMembership(Base, TimestampMixin):
    __tablename__ = "project_memberships"

    id: Mapped[str] = uuid_pk()
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(40), default="owner", nullable=False)

    project: Mapped["Project"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")


class RepositorySnapshot(Base, TimestampMixin):
    __tablename__ = "repository_snapshots"

    id: Mapped[str] = uuid_pk()
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    analyzer_version: Mapped[str] = mapped_column(String(40), default="dna-analyzer-1.0", nullable=False)
    score_model_version: Mapped[str] = mapped_column(String(40), default="dna-core-1.0", nullable=False)
    limits_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    warning_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="snapshots")
    jobs: Mapped[list["AnalysisJob"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")
    files: Mapped[list["FileRecord"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")
    metric_values: Mapped[list["MetricValue"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")
    dna_scores: Mapped[list["DNAScore"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")
    timeline_events: Mapped[list["TimelineEvent"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")


class AnalysisJob(Base, TimestampMixin):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = uuid_pk()
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("repository_snapshots.id", ondelete="CASCADE"), index=True, nullable=False
    )
    state: Mapped[str] = mapped_column(String(30), default="QUEUED", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    phase: Mapped[str | None] = mapped_column(String(60), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lease_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    snapshot: Mapped["RepositorySnapshot"] = relationship(back_populates="jobs")
