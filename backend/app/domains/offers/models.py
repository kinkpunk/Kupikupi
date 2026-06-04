import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (
        UniqueConstraint("store_id", "external_id", name="uq_offer_store_external_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), index=True)
    store_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stores.id"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255))
    product_url: Mapped[str] = mapped_column(String(1000))
    source_price: Mapped[float] = mapped_column(Numeric(12, 2))
    source_old_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    source_currency: Mapped[str] = mapped_column(String(3))
    eur_price: Mapped[float] = mapped_column(Numeric(12, 2))
    eur_old_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    fx_rate_to_eur: Mapped[float | None] = mapped_column(Numeric(12, 6))
    discount_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    availability: Mapped[str] = mapped_column(String(32), default="unknown")
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    availability_items: Mapped[list["OfferAvailability"]] = relationship(
        back_populates="offer",
        cascade="all, delete-orphan",
    )


class OfferAvailability(Base):
    __tablename__ = "offer_availability"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    offer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offers.id", ondelete="CASCADE"),
        index=True,
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("product_variants.id"))
    size_value: Mapped[str | None] = mapped_column(String(64))
    size_system: Mapped[str | None] = mapped_column(String(32))
    color: Mapped[str | None] = mapped_column(String(120))
    in_stock: Mapped[bool] = mapped_column()
    stock_count: Mapped[int | None] = mapped_column()

    offer: Mapped[Offer] = relationship(back_populates="availability_items")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    offer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offers.id", ondelete="CASCADE"),
        index=True,
    )
    source_price: Mapped[float] = mapped_column(Numeric(12, 2))
    source_old_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    source_currency: Mapped[str] = mapped_column(String(3))
    eur_price: Mapped[float] = mapped_column(Numeric(12, 2))
    eur_old_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    fx_rate_to_eur: Mapped[float | None] = mapped_column(Numeric(12, 6))
    discount_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    availability: Mapped[str] = mapped_column(String(32))
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
