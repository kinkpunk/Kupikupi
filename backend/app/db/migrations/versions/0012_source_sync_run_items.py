"""source sync run items

Revision ID: 0012_source_sync_run_items
Revises: 0011_source_product_mappings
Create Date: 2026-06-06 00:00:05.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_source_sync_run_items"
down_revision: str | None = "0011_source_product_mappings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "source_sync_runs",
        sa.Column("failed_offers", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "source_sync_run_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sync_run_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("offer_id", sa.Uuid(), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["sync_run_id"], ["source_sync_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_source_sync_run_items_external_id"),
        "source_sync_run_items",
        ["external_id"],
    )
    op.create_index(
        op.f("ix_source_sync_run_items_offer_id"),
        "source_sync_run_items",
        ["offer_id"],
    )
    op.create_index(
        op.f("ix_source_sync_run_items_product_id"),
        "source_sync_run_items",
        ["product_id"],
    )
    op.create_index(
        op.f("ix_source_sync_run_items_status"),
        "source_sync_run_items",
        ["status"],
    )
    op.create_index(
        op.f("ix_source_sync_run_items_sync_run_id"),
        "source_sync_run_items",
        ["sync_run_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_source_sync_run_items_sync_run_id"), table_name="source_sync_run_items")
    op.drop_index(op.f("ix_source_sync_run_items_status"), table_name="source_sync_run_items")
    op.drop_index(op.f("ix_source_sync_run_items_product_id"), table_name="source_sync_run_items")
    op.drop_index(op.f("ix_source_sync_run_items_offer_id"), table_name="source_sync_run_items")
    op.drop_index(op.f("ix_source_sync_run_items_external_id"), table_name="source_sync_run_items")
    op.drop_table("source_sync_run_items")
    op.drop_column("source_sync_runs", "failed_offers")
