from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: str
    login: str
    display_name: str | None = None
    avatar_url: str | None = None
    github_connected: bool = False

    class Config:
        from_attributes = True


class GitHubRepoOut(BaseModel):
    github_repo_id: int | None = None
    full_name: str
    owner: str
    name: str
    visibility: str = "public"
    default_branch: str = "main"
    description: str | None = None


class ImportProjectIn(BaseModel):
    full_name: str
    branch: str | None = None


class ProjectOut(BaseModel):
    id: str
    full_name: str
    owner: str
    name: str
    visibility: str
    default_branch: str
    description: str | None = None
    is_fixture: bool = False
    latest_snapshot: Any | None = None

    class Config:
        from_attributes = True


class AnalysisJobOut(BaseModel):
    id: str
    snapshot_id: str
    state: str
    progress: int = 0
    phase: str | None = None
    error_code: str | None = None
    error_detail: str | None = None
    attempts: int = 0

    class Config:
        from_attributes = True


class SnapshotOut(BaseModel):
    id: str
    project_id: str
    commit_sha: str
    analyzer_version: str
    score_model_version: str
    status: str
    captured_at: datetime | None = None
    warning_json: dict[str, Any] = Field(default_factory=dict)
    limits_json: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class DecisionIn(BaseModel):
    title: str
    context: str | None = None
    decision_text: str | None = None
    reason: str | None = None
    expected_impact: dict[str, Any] = Field(default_factory=dict)
    status: str = "proposed"
    decided_at: datetime | None = None
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    links: list[dict[str, Any]] = Field(default_factory=list)


class OutcomeReviewIn(BaseModel):
    reviewed_at: datetime
    actual_impact: str | None = None
    evidence: str | None = None
    verdict: str = "neutral"


class ExperimentIn(BaseModel):
    title: str
    hypothesis: str | None = None
    success_criterion: str | None = None
    method: str | None = None
    result: str | None = None
    decision: str = "inconclusive"
    reason: str | None = None
    start_at: datetime | None = None
    evaluated_at: datetime | None = None


class CompareIn(BaseModel):
    snapshot_a: str
    snapshot_b: str


class SummaryIn(BaseModel):
    event_ids: list[str] = Field(default_factory=list)
    max_claims: int = Field(default=5, ge=1, le=20)


class DecisionPatchIn(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    context: str | None = None
    decision_text: str | None = None
    reason: str | None = None
    expected_impact: dict[str, Any] | None = None
    status: str | None = Field(default=None, max_length=40)
    archived: bool | None = None


class ExperimentPatchIn(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    hypothesis: str | None = None
    success_criterion: str | None = None
    method: str | None = None
    result: str | None = None
    decision: str | None = Field(default=None, max_length=40)
    reason: str | None = None
    archived: bool | None = None


class EventPatchIn(BaseModel):
    title: str | None = Field(default=None, max_length=2000)
    summary: str | None = None
    confirmed: bool | None = None


class ErrorOut(BaseModel):
    error: dict[str, Any]