"""source product mappings

Revision ID: 0011_source_product_mappings
Revises: 0010_source_sync_run_config
Create Date: 2026-06-06 00:00:04.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_source_product_mappings"
down_revision: str | None = "0010_source_sync_run_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_product_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("source_config_id", sa.Uuid(), nullable=False),
        sa.Column("external_product_id", sa.String(length=255), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["source_config_id"], ["source_configs.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "store_id",
            "source_config_id",
            "external_product_id",
            name="uq_source_product_mapping_identity",
        ),
    )
    op.create_index(
        op.f("ix_source_product_mappings_external_product_id"),
        "source_product_mappings",
        ["external_product_id"],
    )
    op.create_index(
        op.f("ix_source_product_mappings_product_id"),
        "source_product_mappings",
        ["product_id"],
    )
    op.create_index(
        op.f("ix_source_product_mappings_source_config_id"),
        "source_product_mappings",
        ["source_config_id"],
    )
    op.create_index(
        op.f("ix_source_product_mappings_store_id"),
        "source_product_mappings",
        ["store_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_source_product_mappings_store_id"), table_name="source_product_mappings")
    op.drop_index(
        op.f("ix_source_product_mappings_source_config_id"),
        table_name="source_product_mappings",
    )
    op.drop_index(
        op.f("ix_source_product_mappings_product_id"),
        table_name="source_product_mappings",
    )
    op.drop_index(
        op.f("ix_source_product_mappings_external_product_id"),
        table_name="source_product_mappings",
    )
    op.drop_table("source_product_mappings")
