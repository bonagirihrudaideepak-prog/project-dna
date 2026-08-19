"""add alert rules + alerts tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-19

Adds per-project DNA alert rules and the fired alerts they produce. Additive
only; no existing tables are touched.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        op.Column("id", op.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        op.Column(
            "project_id",
            op.dialects.postgresql.UUID(as_uuid=True),
            op.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        op.Column("dimension", op.String(40), nullable=False),
        op.Column("operator", op.String(4), nullable=False),
        op.Column("threshold", op.Integer(), nullable=False),
        op.Column("enabled", op.Boolean(), nullable=False, server_default=op.text("true")),
        op.Column(
            "created_by",
            op.dialects.postgresql.UUID(as_uuid=True),
            op.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        op.Column("created_at", op.DateTime(timezone=True), server_default=op.func.now(), nullable=False),
        op.Column("updated_at", op.DateTime(timezone=True), server_default=op.func.now(), nullable=False),
        op.UniqueConstraint("project_id", "dimension", name="uq_alert_rules_project_dimension"),
    )
    op.create_index("ix_alert_rules_project_id", "alert_rules", ["project_id"])
    op.create_index("ix_alert_rules_created_by", "alert_rules", ["created_by"])

    op.create_table(
        "alerts",
        op.Column("id", op.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        op.Column(
            "rule_id",
            op.dialects.postgresql.UUID(as_uuid=True),
            op.ForeignKey("alert_rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        op.Column(
            "snapshot_id",
            op.dialects.postgresql.UUID(as_uuid=True),
            op.ForeignKey("repository_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        op.Column("dimension", op.String(40), nullable=False),
        op.Column("old_value", op.Integer(), nullable=True),
        op.Column("new_value", op.Integer(), nullable=True),
        op.Column("fired_at", op.DateTime(timezone=True), server_default=op.func.now(), nullable=False),
        op.Column("acknowledged_at", op.DateTime(timezone=True), nullable=True),
        op.Column("created_at", op.DateTime(timezone=True), server_default=op.func.now(), nullable=False),
        op.Column("updated_at", op.DateTime(timezone=True), server_default=op.func.now(), nullable=False),
        op.UniqueConstraint("rule_id", "snapshot_id", name="uq_alerts_rule_snapshot"),
    )
    op.create_index("ix_alerts_rule_id", "alerts", ["rule_id"])
    op.create_index("ix_alerts_snapshot_id", "alerts", ["snapshot_id"])


def downgrade() -> None:
    op.drop_index("ix_alerts_snapshot_id", table_name="alerts")
    op.drop_index("ix_alerts_rule_id", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_alert_rules_created_by", table_name="alert_rules")
    op.drop_index("ix_alert_rules_project_id", table_name="alert_rules")
    op.drop_table("alert_rules")