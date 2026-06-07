import csv
import uuid
from io import StringIO

import httpx

from app.domains.stores.models import SourceConfig
from app.integrations.stores.base import SourceOfferRecord, StoreSourceAdapter
from app.integrations.stores.static_json import source_offer_record_from_mapping


class HttpCsvSourceAdapter(StoreSourceAdapter):
    source_type = "http_csv"

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
            raise ValueError("HTTP CSV source requires endpoint_url.")

        if self._client is None:
            async with httpx.AsyncClient(timeout=_timeout_seconds(self._source_config)) as client:
                return await _fetch_records(client, self._source_config)
        return await _fetch_records(self._client, self._source_config)


async def _fetch_records(
    client: httpx.AsyncClient,
    source_config: SourceConfig,
) -> list[SourceOfferRecord]:
    response = await client.get(source_config.endpoint_url or "")
    response.raise_for_status()
    settings = source_config.settings or {}
    delimiter = str(settings.get("delimiter", ","))
    rows = csv.DictReader(StringIO(response.text), delimiter=delimiter)
    return [
        source_offer_record_from_mapping(_record_from_csv_row(row, settings))
        for row in rows
        if any(value for value in row.values())
    ]


def _record_from_csv_row(
    row: dict[str, str | None],
    settings: dict[str, object],
) -> dict[str, object]:
    columns = _dict_setting(settings, "columns")
    defaults = _dict_setting(settings, "defaults")
    size_delimiter = str(settings.get("size_delimiter", "|"))

    source_currency = _value(row, columns, "source_currency") or defaults.get(
        "source_currency", "EUR"
    )
    availability = _value(row, columns, "availability") or defaults.get("availability", "unknown")
    category_slug = _value(row, columns, "category_slug") or defaults.get(
        "category_slug", "unknown"
    )
    category_name = _value(row, columns, "category_name") or defaults.get(
        "category_name", category_slug
    )
    external_product_id = _value(row, columns, "external_product_id") or _value(
        row, columns, "external_id"
    )

    return {
        "external_id": _required_value(row, columns, "external_id"),
        "product_url": _required_value(row, columns, "product_url"),
        "source_price": _required_float(row, columns, "source_price"),
        "source_old_price": _optional_float(_value(row, columns, "source_old_price")),
        "source_currency": str(source_currency),
        "eur_price": _optional_float(_value(row, columns, "eur_price")),
        "eur_old_price": _optional_float(_value(row, columns, "eur_old_price")),
        "fx_rate_to_eur": _optional_float(_value(row, columns, "fx_rate_to_eur")),
        "discount_percent": _optional_float(_value(row, columns, "discount_percent")),
        "availability": str(availability),
        "sizes": _sizes_from_value(
            _value(row, columns, "sizes"),
            size_system=_value(row, columns, "size_system")
            or str(defaults.get("size_system", "EU")),
            delimiter=size_delimiter,
        ),
        "product": {
            "external_product_id": external_product_id,
            "name": _required_value(row, columns, "product_name"),
            "brand_name": _value(row, columns, "brand_name"),
            "category_slug": str(category_slug),
            "category_name": str(category_name),
            "model": _value(row, columns, "model"),
            "sku": _value(row, columns, "sku"),
            "image_url": _value(row, columns, "image_url"),
        },
    }


def _dict_setting(settings: dict[str, object], name: str) -> dict[str, object]:
    value = settings.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"HTTP CSV source settings.{name} must be an object.")
    return value


def _value(row: dict[str, str | None], columns: dict[str, object], field: str) -> str | None:
    column_name = str(columns.get(field, field))
    value = row.get(column_name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _required_value(row: dict[str, str | None], columns: dict[str, object], field: str) -> str:
    value = _value(row, columns, field)
    if value is None:
        raise ValueError(f"HTTP CSV source row is missing required field: {field}.")
    return value


def _required_float(row: dict[str, str | None], columns: dict[str, object], field: str) -> float:
    value = _optional_float(_value(row, columns, field))
    if value is None:
        raise ValueError(f"HTTP CSV source row is missing required field: {field}.")
    return value


def _optional_float(value: str | None) -> float | None:
    if value is None:
        return None
    normalized = value.replace(" ", "")
    if "," in normalized and "." not in normalized:
        normalized = normalized.replace(",", ".")
    return float(normalized)


def _sizes_from_value(
    value: str | None,
    *,
    size_system: str,
    delimiter: str,
) -> list[dict[str, object]]:
    if value is None:
        return []
    return [
        {"size_value": size.strip(), "size_system": size_system, "in_stock": True}
        for size in value.split(delimiter)
        if size.strip()
    ]


def _timeout_seconds(source_config: SourceConfig) -> float:
    settings = source_config.settings or {}
    value = settings.get("timeout_seconds", 10)
    return float(value)
