"""notifications

Revision ID: 0008_notifications
Revises: 0007_price_analytics
Create Date: 2026-06-06 00:00:01.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_notifications"
down_revision: str | None = "0007_price_analytics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("watchlist_id", sa.Uuid(), nullable=True),
        sa.Column("shopping_request_id", sa.Uuid(), nullable=True),
        sa.Column("offer_id", sa.Uuid(), nullable=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"]),
        sa.ForeignKeyConstraint(["shopping_request_id"], ["shopping_requests.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["watchlist_id"], ["watchlists.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_notifications_dedupe_key"),
    )
    op.create_index(op.f("ix_notifications_dedupe_key"), "notifications", ["dedupe_key"])
    op.create_index(op.f("ix_notifications_offer_id"), "notifications", ["offer_id"])
    op.create_index(
        op.f("ix_notifications_shopping_request_id"),
        "notifications",
        ["shopping_request_id"],
    )
    op.create_index(op.f("ix_notifications_status"), "notifications", ["status"])
    op.create_index(op.f("ix_notifications_type"), "notifications", ["type"])
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"])
    op.create_index(op.f("ix_notifications_watchlist_id"), "notifications", ["watchlist_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_watchlist_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_type"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_status"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_shopping_request_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_offer_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_dedupe_key"), table_name="notifications")
    op.drop_table("notifications")
