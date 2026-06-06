import uuid

from app.domains.stores.models import SourceConfig
from app.integrations.stores.base import (
    SourceOfferRecord,
    SourceProductRecord,
    StoreSourceAdapter,
)


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
        product_id=_optional_uuid(record.get("product_id")),
        product_url=str(record["product_url"]),
        source_price=float(record["source_price"]),
        source_old_price=_optional_float(record.get("source_old_price")),
        source_currency=str(record["source_currency"]),
        eur_price=_optional_float(record.get("eur_price")),
        eur_old_price=_optional_float(record.get("eur_old_price")),
        fx_rate_to_eur=_optional_float(record.get("fx_rate_to_eur")),
        discount_percent=_optional_float(record.get("discount_percent")),
        availability=str(record.get("availability", "unknown")),
        sizes=_sizes_from_mapping(record.get("sizes", [])),
        product=_product_from_mapping(record.get("product")),
    )


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_uuid(value: object) -> uuid.UUID | None:
    if value is None:
        return None
    return uuid.UUID(str(value))


def _product_from_mapping(value: object) -> SourceProductRecord | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("Static JSON source product must be an object.")
    return SourceProductRecord(
        external_product_id=str(value["external_product_id"]),
        name=str(value["name"]),
        category_slug=str(value["category_slug"]),
        category_name=str(value.get("category_name", value["category_slug"])),
        brand_name=_optional_str(value.get("brand_name")),
        model=_optional_str(value.get("model")),
        sku=_optional_str(value.get("sku")),
        image_url=_optional_str(value.get("image_url")),
        attributes=_optional_dict(value.get("attributes")),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_dict(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("Static JSON source product attributes must be an object.")
    return value


def _sizes_from_mapping(value: object) -> list[dict[str, object]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Static JSON source record sizes must be a list.")
    return [item for item in value if isinstance(item, dict)]
