"""watchlists

Revision ID: 0005_watchlists
Revises: 0004_shopping_requests
Create Date: 2026-06-04 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_watchlists"
down_revision: str | None = "0004_shopping_requests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watchlists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("brand_id", sa.Uuid(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("source_request_id", sa.Uuid(), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("size_value", sa.String(length=64), nullable=True),
        sa.Column("size_system", sa.String(length=32), nullable=True),
        sa.Column("color", sa.String(length=120), nullable=True),
        sa.Column("target_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("target_price_currency", sa.String(length=3), nullable=True),
        sa.Column("discount_threshold", sa.Numeric(5, 2), nullable=True),
        sa.Column("notify_on_historical_min", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(
            ["source_request_id"],
            ["shopping_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_watchlists_brand_id"), "watchlists", ["brand_id"])
    op.create_index(op.f("ix_watchlists_category_id"), "watchlists", ["category_id"])
    op.create_index(op.f("ix_watchlists_product_id"), "watchlists", ["product_id"])
    op.create_index(op.f("ix_watchlists_source_request_id"), "watchlists", ["source_request_id"])
    op.create_index(op.f("ix_watchlists_type"), "watchlists", ["type"])
    op.create_index(op.f("ix_watchlists_user_id"), "watchlists", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_watchlists_user_id"), table_name="watchlists")
    op.drop_index(op.f("ix_watchlists_type"), table_name="watchlists")
    op.drop_index(op.f("ix_watchlists_source_request_id"), table_name="watchlists")
    op.drop_index(op.f("ix_watchlists_product_id"), table_name="watchlists")
    op.drop_index(op.f("ix_watchlists_category_id"), table_name="watchlists")
    op.drop_index(op.f("ix_watchlists_brand_id"), table_name="watchlists")
    op.drop_table("watchlists")

