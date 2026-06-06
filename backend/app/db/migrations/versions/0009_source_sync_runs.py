"""source sync runs

Revision ID: 0009_source_sync_runs
Revises: 0008_notifications
Create Date: 2026-06-06 00:00:02.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_source_sync_runs"
down_revision: str | None = "0008_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_sync_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("products_seen", sa.Integer(), nullable=False),
        sa.Column("offers_seen", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_source_sync_runs_status"), "source_sync_runs", ["status"])
    op.create_index(op.f("ix_source_sync_runs_store_id"), "source_sync_runs", ["store_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_source_sync_runs_store_id"), table_name="source_sync_runs")
    op.drop_index(op.f("ix_source_sync_runs_status"), table_name="source_sync_runs")
    op.drop_table("source_sync_runs")
