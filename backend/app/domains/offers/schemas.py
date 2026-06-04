import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OfferAvailabilityCreate(BaseModel):
    variant_id: uuid.UUID | None = None
    size_value: str | None = None
    size_system: str | None = None
    color: str | None = None
    in_stock: bool = True
    stock_count: int | None = None


class OfferAvailabilityRead(OfferAvailabilityCreate):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class OfferCreate(BaseModel):
    product_id: uuid.UUID
    store_id: uuid.UUID
    external_id: str | None = None
    product_url: str
    source_price: float
    source_old_price: float | None = None
    source_currency: str
    eur_price: float
    eur_old_price: float | None = None
    fx_rate_to_eur: float | None = None
    discount_percent: float | None = None
    availability: str = "unknown"
    availability_items: list[OfferAvailabilityCreate] = []


class OfferUpdate(BaseModel):
    product_url: str | None = None
    source_price: float | None = None
    source_old_price: float | None = None
    source_currency: str | None = None
    eur_price: float | None = None
    eur_old_price: float | None = None
    fx_rate_to_eur: float | None = None
    discount_percent: float | None = None
    availability: str | None = None


class StoreSummary(BaseModel):
    id: uuid.UUID
    name: str
    url: str

    model_config = ConfigDict(from_attributes=True)


class OfferRead(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    store_id: uuid.UUID
    external_id: str | None
    product_url: str
    source_price: float
    source_old_price: float | None
    source_currency: str
    eur_price: float
    eur_old_price: float | None
    fx_rate_to_eur: float | None
    discount_percent: float | None
    availability: str
    last_seen_at: datetime
    availability_items: list[OfferAvailabilityRead]

    model_config = ConfigDict(from_attributes=True)


class OfferList(BaseModel):
    items: list[OfferRead]
    total: int


class PricePoint(BaseModel):
    captured_at: datetime
    source_price: float
    source_old_price: float | None
    source_currency: str
    eur_price: float
    eur_old_price: float | None
    fx_rate_to_eur: float | None
    discount_percent: float | None
    availability: str
    store_id: uuid.UUID


class PriceHistoryResponse(BaseModel):
    product_id: uuid.UUID
    period: str
    points: list[PricePoint]

