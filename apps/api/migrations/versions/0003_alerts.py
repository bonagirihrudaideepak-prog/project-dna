"""add alert rules + alerts tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-19

Adds per-project DNA alert rules and the fired alerts they produce. Additive
only; no existing tables are touched.

Note: 0001 bootstraps via ``Base.metadata.create_all`` (the full current model
schema), so on databases initialized that way these tables already exist.
Creation is therefore guarded to keep the chain runnable from scratch. The
original revision used a nonexistent ``op.Column`` helper and never applied
successfully anywhere; it was corrected in place before first deployment.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, name: str) -> bool:
    return name in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, "alert_rules"):
        op.create_table(
            "alert_rules",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "project_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("projects.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("dimension", sa.String(40), nullable=False),
            sa.Column("operator", sa.String(4), nullable=False),
            sa.Column("threshold", sa.Integer(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column(
                "created_by",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("project_id", "dimension", name="uq_alert_rules_project_dimension"),
        )
    op.create_index("ix_alert_rules_project_id", "alert_rules", ["project_id"], if_not_exists=True)
    op.create_index("ix_alert_rules_created_by", "alert_rules", ["created_by"], if_not_exists=True)

    if not _table_exists(bind, "alerts"):
        op.create_table(
            "alerts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "rule_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("alert_rules.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "snapshot_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("repository_snapshots.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("dimension", sa.String(40), nullable=False),
            sa.Column("old_value", sa.Integer(), nullable=True),
            sa.Column("new_value", sa.Integer(), nullable=True),
            sa.Column("fired_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("rule_id", "snapshot_id", name="uq_alerts_rule_snapshot"),
        )
    op.create_index("ix_alerts_rule_id", "alerts", ["rule_id"], if_not_exists=True)
    op.create_index("ix_alerts_snapshot_id", "alerts", ["snapshot_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_alerts_snapshot_id", table_name="alerts")
    op.drop_index("ix_alerts_rule_id", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_alert_rules_created_by", table_name="alert_rules")
    op.drop_index("ix_alert_rules_project_id", table_name="alert_rules")
    op.drop_table("alert_rules")
