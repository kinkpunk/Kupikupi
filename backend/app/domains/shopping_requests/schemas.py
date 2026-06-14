import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.catalog.schemas import ProductRead


class ShoppingRequestCreate(BaseModel):
    text: str
    create_watchlist_after_confirmation: bool = False


class ShoppingRequestUpdate(BaseModel):
    text: str


class ShoppingConstraintsRead(BaseModel):
    category: str | None
    use_case: str | None
    size_value: str | None
    size_system: str | None
    preferred_brand: str | None
    color: str | None
    max_price: float | None
    max_price_currency: str | None
    attributes: dict[str, object] | None

    model_config = ConfigDict(from_attributes=True)


class ShoppingRequestRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    raw_text: str
    status: str
    locale: str
    display_currency: str | None
    budget_amount: float | None
    constraints: ShoppingConstraintsRead | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShoppingRequestList(BaseModel):
    items: list[ShoppingRequestRead]
    total: int


class RecommendationRead(BaseModel):
    id: uuid.UUID
    product: ProductRead
    best_offer_id: uuid.UUID | None
    score: float
    reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecommendationList(BaseModel):
    items: list[RecommendationRead]
