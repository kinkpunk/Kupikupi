import uuid

from app.domains.stores.models import SourceConfig
from app.integrations.stores.base import SourceOfferRecord, StoreSourceAdapter


class StaticJsonSourceAdapter(StoreSourceAdapter):
    source_type = "static_json"

    def __init__(self, source_config: SourceConfig) -> None:
        self._source_config = source_config

    async def fetch_offers(self, *, store_id: uuid.UUID | None = None) -> list[SourceOfferRecord]:
        settings = self._source_config.settings or {}
        records = settings.get("records", [])
        if not isinstance(records, list):
            raise ValueError("Static JSON source settings.records must be a list.")
        return [_record_from_mapping(record) for record in records]


def _record_from_mapping(record: object) -> SourceOfferRecord:
    if not isinstance(record, dict):
        raise ValueError("Static JSON source record must be an object.")

    return SourceOfferRecord(
        external_id=str(record["external_id"]),
        product_id=uuid.UUID(str(record["product_id"])),
        product_url=str(record["product_url"]),
        source_price=float(record["source_price"]),
        source_old_price=_optional_float(record.get("source_old_price")),
        source_currency=str(record["source_currency"]),
        eur_price=float(record["eur_price"]),
        eur_old_price=_optional_float(record.get("eur_old_price")),
        fx_rate_to_eur=_optional_float(record.get("fx_rate_to_eur")),
        discount_percent=_optional_float(record.get("discount_percent")),
        availability=str(record.get("availability", "unknown")),
        sizes=_sizes_from_mapping(record.get("sizes", [])),
    )


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _sizes_from_mapping(value: object) -> list[dict[str, object]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Static JSON source record sizes must be a list.")
    return [item for item in value if isinstance(item, dict)]
