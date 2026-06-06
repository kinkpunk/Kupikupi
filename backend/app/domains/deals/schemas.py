import uuid

from pydantic import BaseModel

from app.domains.offers.schemas import OfferRead


class DealRead(BaseModel):
    offer: OfferRead
    product_id: uuid.UUID
    category_id: uuid.UUID
    brand_id: uuid.UUID | None
    score: float
    reasons: list[str]


class DealList(BaseModel):
    items: list[DealRead]
    total: int

