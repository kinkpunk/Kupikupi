import uuid

import httpx

from app.domains.stores.models import SourceConfig
from app.integrations.stores.base import SourceOfferRecord, StoreSourceAdapter
from app.integrations.stores.static_json import source_offer_record_from_mapping


class HttpJsonSourceAdapter(StoreSourceAdapter):
    source_type = "http_json"

    def __init__(
        self,
        source_config: SourceConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._source_config = source_config
        self._client = client

    async def fetch_offers(self, *, store_id: uuid.UUID | None = None) -> list[SourceOfferRecord]:
        if not self._source_config.endpoint_url:
            raise ValueError("HTTP JSON source requires endpoint_url.")

        if self._client is None:
            async with httpx.AsyncClient(timeout=_timeout_seconds(self._source_config)) as client:
                return await _fetch_records(client, self._source_config.endpoint_url)
        return await _fetch_records(self._client, self._source_config.endpoint_url)


async def _fetch_records(
    client: httpx.AsyncClient,
    endpoint_url: str,
) -> list[SourceOfferRecord]:
    response = await client.get(endpoint_url)
    response.raise_for_status()
    payload = response.json()
    records = _records_from_payload(payload)
    return [source_offer_record_from_mapping(record) for record in records]


def _records_from_payload(payload: object) -> list[object]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        records = payload.get("records")
        if isinstance(records, list):
            return records
    raise ValueError("HTTP JSON source response must be a list or an object with records list.")


def _timeout_seconds(source_config: SourceConfig) -> float:
    settings = source_config.settings or {}
    value = settings.get("timeout_seconds", 10)
    return float(value)
