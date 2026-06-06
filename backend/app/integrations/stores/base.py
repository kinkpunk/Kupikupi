import uuid
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class SourceOfferRecord:
    external_id: str
    product_id: uuid.UUID
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


class StoreSourceAdapter(Protocol):
    source_type: str

    async def fetch_offers(self, *, store_id: uuid.UUID | None = None) -> list[SourceOfferRecord]:
        pass


class UnknownSourceTypeError(ValueError):
    pass
