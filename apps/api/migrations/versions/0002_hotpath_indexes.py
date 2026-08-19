"""add queue + snapshot hot-path indexes

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-19

The worker claim query filters on ``analysis_jobs.state`` ordered by
``created_at``; the project dashboard joins snapshots on
``project_id``/``created_at``. Both are hot at scale.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "605daba23479"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_analysis_jobs_state", "analysis_jobs", ["state"])
    op.create_index("ix_analysis_jobs_created_at", "analysis_jobs", ["created_at"])
    op.create_index(
        "ix_repository_snapshots_project_id_created_at",
        "repository_snapshots",
        ["project_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_repository_snapshots_project_id_created_at", table_name="repository_snapshots")
    op.drop_index("ix_analysis_jobs_created_at", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_state", table_name="analysis_jobs")