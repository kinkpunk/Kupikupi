"""fx rates

Revision ID: 0014_fx_rates
Revises: 0013_source_config_schedule
Create Date: 2026-06-06 00:00:07.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_fx_rates"
down_revision: str | None = "0013_source_config_schedule"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fx_rates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("rate_to_eur", sa.Numeric(12, 6), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("valid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("currency", "valid_at", name="uq_fx_rate_currency_valid_at"),
    )
    op.create_index(op.f("ix_fx_rates_currency"), "fx_rates", ["currency"])
    op.create_index(op.f("ix_fx_rates_valid_at"), "fx_rates", ["valid_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_fx_rates_valid_at"), table_name="fx_rates")
    op.drop_index(op.f("ix_fx_rates_currency"), table_name="fx_rates")
    op.drop_table("fx_rates")
