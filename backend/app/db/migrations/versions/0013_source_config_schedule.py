"""source config schedule

Revision ID: 0013_source_config_schedule
Revises: 0012_source_sync_run_items
Create Date: 2026-06-06 00:00:06.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_source_config_schedule"
down_revision: str | None = "0012_source_sync_run_items"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "source_configs",
        sa.Column("sync_interval_minutes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "source_configs",
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "source_configs",
        sa.Column("next_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_source_configs_next_sync_at"), "source_configs", ["next_sync_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_source_configs_next_sync_at"), table_name="source_configs")
    op.drop_column("source_configs", "next_sync_at")
    op.drop_column("source_configs", "last_sync_at")
    op.drop_column("source_configs", "sync_interval_minutes")
