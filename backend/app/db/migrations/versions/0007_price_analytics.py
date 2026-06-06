"""price analytics

Revision ID: 0007_price_analytics
Revises: 0006_offers_and_price_snapshots
Create Date: 2026-06-06 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_price_analytics"
down_revision: str | None = "0006_offers_and_price_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "price_analytics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=True),
        sa.Column("eur_min_30d", sa.Numeric(12, 2), nullable=True),
        sa.Column("eur_min_90d", sa.Numeric(12, 2), nullable=True),
        sa.Column("eur_min_180d", sa.Numeric(12, 2), nullable=True),
        sa.Column("eur_min_365d", sa.Numeric(12, 2), nullable=True),
        sa.Column("eur_min_all_time", sa.Numeric(12, 2), nullable=True),
        sa.Column("eur_avg_365d", sa.Numeric(12, 2), nullable=True),
        sa.Column("eur_lowest_10pct_365d_threshold", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_price_analytics_product_id"), "price_analytics", ["product_id"])
    op.create_index(op.f("ix_price_analytics_store_id"), "price_analytics", ["store_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_price_analytics_store_id"), table_name="price_analytics")
    op.drop_index(op.f("ix_price_analytics_product_id"), table_name="price_analytics")
    op.drop_table("price_analytics")

