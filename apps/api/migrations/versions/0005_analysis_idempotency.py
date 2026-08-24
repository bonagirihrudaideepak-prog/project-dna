"""make analysis results idempotent across worker retries

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-24

Worker RETRY re-runs the analysis pipeline for the same snapshot. Without
uniqueness, partially committed rows from a failed attempt were re-inserted on
every retry, doubling residue and corrupting scores. This migration:
  1. removes existing duplicates (keeping the newest row), so it is safe to run
     on databases that already accumulated residue, and
  2. adds unique indexes so any future double-write fails loudly.

Additive only: no column changes, no data loss beyond exact duplicates.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# table -> unique key columns (all also carry an index on snapshot_id)
_UNIQUE_KEYS = [
    ("dna_scores", ["snapshot_id", "dimension"]),
    ("metric_values", ["snapshot_id", "key"]),
    ("artifacts", ["snapshot_id", "type", "provider_id"]),
    ("files", ["snapshot_id", "path"]),
]

# graph_nodes.snapshot_id is nullable -> partial unique index
_PARTIAL_UNIQUE_KEYS = [
    ("graph_nodes", ["snapshot_id", "entity_type", "entity_id"], "snapshot_id IS NOT NULL"),
]


def _dedupe(table: str, cols: list[str]) -> None:
    a_cols = ", ".join(f"a.{c}" for c in cols)
    b_cols = ", ".join(f"b.{c}" for c in cols)
    # Row-value comparison gives a deterministic newest-row tie-break.
    op.execute(
        f"DELETE FROM {table} a USING {table} b "
        f"WHERE ({a_cols}) = ({b_cols}) "
        f"AND (a.created_at, a.id) < (b.created_at, b.id)"
    )


def upgrade() -> None:
    for table, cols in _UNIQUE_KEYS:
        _dedupe(table, cols)
        op.create_index(
            f"ux_{table}_{'_'.join(cols)}",
            table,
            cols,
            unique=True,
        )
    for table, cols, predicate in _PARTIAL_UNIQUE_KEYS:
        _dedupe(table, cols)
        op.create_index(
            f"ux_{table}_{'_'.join(cols)}",
            table,
            cols,
            unique=True,
            postgresql_where=predicate,
        )


def downgrade() -> None:
    for table, cols, _predicate in _PARTIAL_UNIQUE_KEYS:
        op.drop_index(f"ux_{table}_{'_'.join(cols)}", table_name=table)
    for table, cols in _UNIQUE_KEYS:
        op.drop_index(f"ux_{table}_{'_'.join(cols)}", table_name=table)
