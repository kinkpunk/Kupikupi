"""shopping requests

Revision ID: 0004_shopping_requests
Revises: 0003_catalog_and_stores
Create Date: 2026-05-30 00:00:03.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_shopping_requests"
down_revision: str | None = "0003_catalog_and_stores"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shopping_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("display_currency", sa.String(length=3), nullable=True),
        sa.Column("budget_amount", sa.Numeric(12, 2), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shopping_requests_user_id"), "shopping_requests", ["user_id"])

    op.create_table(
        "shopping_request_constraints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("use_case", sa.String(length=255), nullable=True),
        sa.Column("size_value", sa.String(length=64), nullable=True),
        sa.Column("size_system", sa.String(length=32), nullable=True),
        sa.Column("preferred_brand", sa.String(length=255), nullable=True),
        sa.Column("color", sa.String(length=120), nullable=True),
        sa.Column("max_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("max_price_currency", sa.String(length=3), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["shopping_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index(
        op.f("ix_shopping_request_constraints_request_id"),
        "shopping_request_constraints",
        ["request_id"],
    )

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("best_offer_id", sa.Uuid(), nullable=True),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["shopping_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recommendations_best_offer_id"), "recommendations", ["best_offer_id"])
    op.create_index(op.f("ix_recommendations_product_id"), "recommendations", ["product_id"])
    op.create_index(op.f("ix_recommendations_request_id"), "recommendations", ["request_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_recommendations_request_id"), table_name="recommendations")
    op.drop_index(op.f("ix_recommendations_product_id"), table_name="recommendations")
    op.drop_index(op.f("ix_recommendations_best_offer_id"), table_name="recommendations")
    op.drop_table("recommendations")
    op.drop_index(
        op.f("ix_shopping_request_constraints_request_id"),
        table_name="shopping_request_constraints",
    )
    op.drop_table("shopping_request_constraints")
    op.drop_index(op.f("ix_shopping_requests_user_id"), table_name="shopping_requests")
    op.drop_table("shopping_requests")
