"""source sync run config

Revision ID: 0010_source_sync_run_config
Revises: 0009_source_sync_runs
Create Date: 2026-06-06 00:00:03.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_source_sync_run_config"
down_revision: str | None = "0009_source_sync_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("source_sync_runs", sa.Column("source_config_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_source_sync_runs_source_config_id"),
        "source_sync_runs",
        ["source_config_id"],
    )
    op.create_foreign_key(
        "fk_source_sync_runs_source_config_id_source_configs",
        "source_sync_runs",
        "source_configs",
        ["source_config_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_source_sync_runs_source_config_id_source_configs",
        "source_sync_runs",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_source_sync_runs_source_config_id"), table_name="source_sync_runs")
    op.drop_column("source_sync_runs", "source_config_id")
