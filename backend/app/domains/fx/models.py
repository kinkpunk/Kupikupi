import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FxRate(Base):
    __tablename__ = "fx_rates"
    __table_args__ = (
        UniqueConstraint("currency", "valid_at", name="uq_fx_rate_currency_valid_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    currency: Mapped[str] = mapped_column(String(3), index=True)
    rate_to_eur: Mapped[float] = mapped_column(Numeric(12, 6))
    source: Mapped[str] = mapped_column(String(64), default="manual")
    valid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
