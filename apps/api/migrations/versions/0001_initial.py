"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-14

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.models import Base

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS score_evidence CASCADE")
    op.execute("DROP TABLE IF EXISTS dna_scores CASCADE")
    op.execute("DROP TABLE IF EXISTS metric_values CASCADE")
    op.execute("DROP TABLE IF EXISTS file_changes CASCADE")
    op.execute("DROP TABLE IF EXISTS files CASCADE")
    op.execute("DROP TABLE IF EXISTS artifacts CASCADE")
    op.execute("DROP TABLE IF EXISTS event_artifacts CASCADE")
    op.execute("DROP TABLE IF EXISTS event_components CASCADE")
    op.execute("DROP TABLE IF EXISTS timeline_events CASCADE")
    op.execute("DROP TABLE IF EXISTS decision_alternatives CASCADE")
    op.execute("DROP TABLE IF EXISTS decision_links CASCADE")
    op.execute("DROP TABLE IF EXISTS outcome_reviews CASCADE")
    op.execute("DROP TABLE IF EXISTS decisions CASCADE")
    op.execute("DROP TABLE IF EXISTS experiment_links CASCADE")
    op.execute("DROP TABLE IF EXISTS experiments CASCADE")
    op.execute("DROP TABLE IF EXISTS components CASCADE")
    op.execute("DROP TABLE IF EXISTS graph_edges CASCADE")
    op.execute("DROP TABLE IF EXISTS graph_nodes CASCADE")
    op.execute("DROP TABLE IF EXISTS llm_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS audit_events CASCADE")
    op.execute("DROP TABLE IF EXISTS exports CASCADE")
    op.execute("DROP TABLE IF EXISTS analysis_jobs CASCADE")
    op.execute("DROP TABLE IF EXISTS repository_snapshots CASCADE")
    op.execute("DROP TABLE IF EXISTS project_memberships CASCADE")
    op.execute("DROP TABLE IF EXISTS github_connections CASCADE")
    op.execute("DROP TABLE IF EXISTS projects CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")