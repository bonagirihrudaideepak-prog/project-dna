"""worker claim query partial index

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-24

The worker claims jobs with:

    WHERE state IN ('QUEUED','RETRY')
      AND attempts < :n AND (lease_until IS NULL OR lease_until < :now)
    ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED

A single partial index covering the state filter plus ordering lets Postgres
satisfy the claim from a narrow, pre-sorted slice instead of reconciling the
separate ix_analysis_jobs_state and ix_analysis_jobs_created_at indexes.
Additive only.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_analysis_jobs_claimable",
        "analysis_jobs",
        ["created_at"],
        postgresql_where="state IN ('QUEUED', 'RETRY')",
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_jobs_claimable", table_name="analysis_jobs")
