import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    country: Mapped[str] = mapped_column(String(2), default="CZ")
    url: Mapped[str] = mapped_column(String(1000))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    delivers_to_cz: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_configs: Mapped[list["SourceConfig"]] = relationship(
        back_populates="store",
        cascade="all, delete-orphan",
    )


class SourceConfig(Base):
    __tablename__ = "source_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"))
    source_type: Mapped[str] = mapped_column(String(64))
    endpoint_url: Mapped[str | None] = mapped_column(String(1000))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_interval_minutes: Mapped[int | None] = mapped_column(Integer)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    settings: Mapped[dict[str, object] | None] = mapped_column(JSON)

    store: Mapped[Store] = relationship(back_populates="source_configs")


class SourceProductMapping(Base):
    __tablename__ = "source_product_mappings"
    __table_args__ = (
        UniqueConstraint(
            "store_id",
            "source_config_id",
            "external_product_id",
            name="uq_source_product_mapping_identity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stores.id"), index=True)
    source_config_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_configs.id"), index=True)
    external_product_id: Mapped[str] = mapped_column(String(255), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), index=True)
    raw_data: Mapped[dict[str, object] | None] = mapped_column(JSON)


class SourceSyncRun(Base):
    __tablename__ = "source_sync_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stores.id"), index=True)
    source_config_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_configs.id"),
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(64), default="fake")
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    products_seen: Mapped[int] = mapped_column(Integer, default=0)
    offers_seen: Mapped[int] = mapped_column(Integer, default=0)
    failed_offers: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(String(1000))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourceSyncRunItem(Base):
    __tablename__ = "source_sync_run_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sync_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_sync_runs.id", ondelete="CASCADE"),
        index=True,
    )
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id"), index=True)
    offer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("offers.id"), index=True)
    error_message: Mapped[str | None] = mapped_column(String(1000))
    raw_data: Mapped[dict[str, object] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
