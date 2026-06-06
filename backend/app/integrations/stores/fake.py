import uuid

from app.integrations.stores.base import SourceOfferRecord, StoreSourceAdapter


class FakeStoreSourceAdapter(StoreSourceAdapter):
    source_type = "fake"

    def __init__(self, records: list[SourceOfferRecord] | None = None) -> None:
        self._records = records or []

    async def fetch_offers(self, *, store_id: uuid.UUID | None = None) -> list[SourceOfferRecord]:
        return self._records

