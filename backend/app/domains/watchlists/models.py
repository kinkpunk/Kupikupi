import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    type: Mapped[str] = mapped_column(String(32), index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id"), index=True)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("brands.id"), index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"), index=True)
    source_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("shopping_requests.id", ondelete="SET NULL"),
        index=True,
    )
    model: Mapped[str | None] = mapped_column(String(255))
    size_value: Mapped[str | None] = mapped_column(String(64))
    size_system: Mapped[str | None] = mapped_column(String(32))
    color: Mapped[str | None] = mapped_column(String(120))
    target_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    target_price_currency: Mapped[str | None] = mapped_column(String(3))
    discount_threshold: Mapped[float | None] = mapped_column(Numeric(5, 2))
    notify_on_historical_min: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

