import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.domains.catalog.models import Product
    from app.domains.watchlists.models import Watchlist


class ShoppingRequest(Base):
    __tablename__ = "shopping_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    raw_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="created")
    locale: Mapped[str] = mapped_column(String(16), default="ru")
    display_currency: Mapped[str | None] = mapped_column(String(3))
    budget_amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    constraints: Mapped["ShoppingRequestConstraints | None"] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
        uselist=False,
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
    )
    watchlists: Mapped[list["Watchlist"]] = relationship(
        back_populates="source_request",
        foreign_keys="Watchlist.source_request_id",
    )

    @property
    def editable(self) -> bool:
        return not self.watchlists


class ShoppingRequestConstraints(Base):
    __tablename__ = "shopping_request_constraints"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shopping_requests.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    category: Mapped[str | None] = mapped_column(String(120))
    use_case: Mapped[str | None] = mapped_column(String(255))
    size_value: Mapped[str | None] = mapped_column(String(64))
    size_system: Mapped[str | None] = mapped_column(String(32))
    preferred_brand: Mapped[str | None] = mapped_column(String(255))
    color: Mapped[str | None] = mapped_column(String(120))
    max_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    max_price_currency: Mapped[str | None] = mapped_column(String(3))
    attributes: Mapped[dict[str, object] | None] = mapped_column(JSON)

    request: Mapped[ShoppingRequest] = relationship(back_populates="constraints")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shopping_requests.id", ondelete="CASCADE"),
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), index=True)
    best_offer_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    score: Mapped[float] = mapped_column(Numeric(5, 2))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request: Mapped[ShoppingRequest] = relationship(back_populates="recommendations")
    product: Mapped["Product"] = relationship()
