import uuid
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class SourceProductRecord:
    external_product_id: str
    name: str
    category_slug: str
    category_name: str
    brand_name: str | None = None
    model: str | None = None
    sku: str | None = None
    image_url: str | None = None
    attributes: dict[str, object] | None = None


@dataclass(frozen=True)
class SourceOfferRecord:
    external_id: str
    product_id: uuid.UUID | None
    product_url: str
    source_price: float
    source_old_price: float | None
    source_currency: str
    eur_price: float
    eur_old_price: float | None
    fx_rate_to_eur: float | None
    discount_percent: float | None
    availability: str
    sizes: list[dict[str, object]] = field(default_factory=list)
    product: SourceProductRecord | None = None


class StoreSourceAdapter(Protocol):
    source_type: str

    async def fetch_offers(self, *, store_id: uuid.UUID | None = None) -> list[SourceOfferRecord]:
        pass


class UnknownSourceTypeError(ValueError):
    pass
