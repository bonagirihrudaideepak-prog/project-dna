"""add alerts inbox index

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-20

The alert inbox (GET /alerts) filters on acknowledged_at IS NULL and orders by
fired_at DESC. Without a supporting index this becomes a full scan + sort on the
alerts table once it grows. Additive only.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_alerts_acknowledged_at_fired_at",
        "alerts",
        ["acknowledged_at", "fired_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_alerts_acknowledged_at_fired_at", table_name="alerts")