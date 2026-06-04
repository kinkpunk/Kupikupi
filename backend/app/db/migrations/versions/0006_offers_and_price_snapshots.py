"""offers and price snapshots

Revision ID: 0006_offers_and_price_snapshots
Revises: 0005_watchlists
Create Date: 2026-06-04 00:00:01.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_offers_and_price_snapshots"
down_revision: str | None = "0005_watchlists"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "offers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("product_url", sa.String(length=1000), nullable=False),
        sa.Column("source_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("source_old_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("source_currency", sa.String(length=3), nullable=False),
        sa.Column("eur_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("eur_old_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("fx_rate_to_eur", sa.Numeric(12, 6), nullable=True),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("availability", sa.String(length=32), nullable=False),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "external_id", name="uq_offer_store_external_id"),
    )
    op.create_index(op.f("ix_offers_product_id"), "offers", ["product_id"])
    op.create_index(op.f("ix_offers_store_id"), "offers", ["store_id"])

    op.create_table(
        "offer_availability",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=True),
        sa.Column("size_value", sa.String(length=64), nullable=True),
        sa.Column("size_system", sa.String(length=32), nullable=True),
        sa.Column("color", sa.String(length=120), nullable=True),
        sa.Column("in_stock", sa.Boolean(), nullable=False),
        sa.Column("stock_count", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_offer_availability_offer_id"), "offer_availability", ["offer_id"])

    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=False),
        sa.Column("source_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("source_old_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("source_currency", sa.String(length=3), nullable=False),
        sa.Column("eur_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("eur_old_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("fx_rate_to_eur", sa.Numeric(12, 6), nullable=True),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("availability", sa.String(length=32), nullable=False),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_price_snapshots_offer_id"), "price_snapshots", ["offer_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_price_snapshots_offer_id"), table_name="price_snapshots")
    op.drop_table("price_snapshots")
    op.drop_index(op.f("ix_offer_availability_offer_id"), table_name="offer_availability")
    op.drop_table("offer_availability")
    op.drop_index(op.f("ix_offers_store_id"), table_name="offers")
    op.drop_index(op.f("ix_offers_product_id"), table_name="offers")
    op.drop_table("offers")

