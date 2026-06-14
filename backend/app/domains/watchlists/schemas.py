import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class WatchlistType(StrEnum):
    exact_product = "exact_product"
    category_rule = "category_rule"
    brand_rule = "brand_rule"
    agent_request = "agent_request"


class WatchlistCreate(BaseModel):
    type: WatchlistType
    product_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    source_request_id: uuid.UUID | None = None
    model: str | None = None
    size_value: str | None = None
    size_system: str | None = None
    color: str | None = None
    target_price: float | None = None
    target_price_currency: str | None = None
    discount_threshold: float | None = None
    notify_on_historical_min: bool = True


class WatchlistUpdate(BaseModel):
    type: WatchlistType | None = None
    product_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    model: str | None = None
    size_value: str | None = None
    size_system: str | None = None
    color: str | None = None
    target_price: float | None = None
    target_price_currency: str | None = None
    discount_threshold: float | None = None
    notify_on_historical_min: bool | None = None
    active: bool | None = None
    archived: bool | None = None


class WatchlistRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: WatchlistType
    product_id: uuid.UUID | None
    brand_id: uuid.UUID | None
    category_id: uuid.UUID | None
    category: str | None
    brand: str | None
    use_case: str | None
    source_request_id: uuid.UUID | None
    model: str | None
    size_value: str | None
    size_system: str | None
    color: str | None
    target_price: float | None
    target_price_currency: str | None
    discount_threshold: float | None
    notify_on_historical_min: bool
    active: bool
    archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WatchlistList(BaseModel):
    items: list[WatchlistRead]
    total: int
