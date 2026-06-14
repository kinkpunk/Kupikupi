import uuid
from xml.etree import ElementTree

import httpx

from app.domains.stores.models import SourceConfig
from app.integrations.stores.base import (
    SourceOfferRecord,
    SourceProductRecord,
    StoreSourceAdapter,
)


class HeurekaXmlSourceAdapter(StoreSourceAdapter):
    source_type = "heureka_xml"

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
            raise ValueError("Heureka XML source requires endpoint_url.")

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
    return _records_from_xml(response.content, source_config.settings or {})


def _records_from_xml(
    content: bytes,
    settings: dict[str, object],
) -> list[SourceOfferRecord]:
    if b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
        raise ValueError("Heureka XML source must not contain DTD or entity declarations.")
    root = ElementTree.fromstring(content)
    if _tag_name(root.tag) != "SHOP":
        raise ValueError("Heureka XML source root element must be SHOP.")

    records = []
    for item in root:
        if _tag_name(item.tag) != "SHOPITEM":
            continue
        records.append(_record_from_item(item, settings))
    return records


def _record_from_item(
    item: ElementTree.Element,
    settings: dict[str, object],
) -> SourceOfferRecord:
    item_id = _required_text(item, "ITEM_ID")
    product_name = _text(item, "PRODUCTNAME") or _required_text(item, "PRODUCT")
    category_text = _text(item, "CATEGORYTEXT") or "Uncategorized"
    category_slug, category_name = _map_category(category_text, settings)
    params = _params(item)
    size = _first_param(params, _setting_names(settings, "size_param_names", ["velikost", "size"]))
    color = _first_param(
        params,
        _setting_names(settings, "color_param_names", ["barva", "colour", "color"]),
    )
    delivery_date = _text(item, "DELIVERY_DATE")
    availability = _availability(delivery_date)
    item_group_id = _text(item, "ITEMGROUP_ID")

    return SourceOfferRecord(
        external_id=item_id,
        product_id=None,
        product_url=_required_text(item, "URL"),
        source_price=_required_float(item, "PRICE_VAT"),
        source_old_price=None,
        source_currency=str(settings.get("source_currency", "CZK")).upper(),
        eur_price=None,
        eur_old_price=None,
        fx_rate_to_eur=None,
        discount_percent=None,
        availability=availability,
        sizes=[
            {
                "size_value": size,
                "size_system": str(settings.get("size_system", "EU")),
                "color": color,
                "in_stock": True,
            }
        ]
        if size or color
        else [],
        product=SourceProductRecord(
            external_product_id=item_group_id or item_id,
            name=product_name,
            category_slug=category_slug,
            category_name=category_name,
            brand_name=_text(item, "MANUFACTURER"),
            model=_text(item, "PRODUCT"),
            sku=_text(item, "EAN"),
            image_url=_text(item, "IMGURL"),
            attributes={
                "heureka_category": category_text,
                "delivery_days": delivery_date,
                "parameters": params,
            },
        ),
    )


def _map_category(
    category_text: str,
    settings: dict[str, object],
) -> tuple[str, str]:
    category_map = settings.get("category_map", {})
    if not isinstance(category_map, dict):
        raise ValueError("Heureka XML source settings.category_map must be an object.")

    normalized_category = category_text.casefold()
    for source_term, target in category_map.items():
        if str(source_term).casefold() not in normalized_category:
            continue
        if isinstance(target, str):
            return target, _title_from_slug(target)
        if isinstance(target, dict):
            slug = str(target.get("slug", "")).strip()
            if not slug:
                raise ValueError("Heureka XML category mapping must include slug.")
            return slug, str(target.get("name") or _title_from_slug(slug))

    default_slug = str(settings.get("default_category_slug", "unknown"))
    default_name = str(settings.get("default_category_name", _title_from_slug(default_slug)))
    return default_slug, default_name


def _params(item: ElementTree.Element) -> dict[str, str]:
    values: dict[str, str] = {}
    for child in item:
        if _tag_name(child.tag) != "PARAM":
            continue
        name = _text(child, "PARAM_NAME")
        value = _text(child, "VAL")
        if name and value:
            values[name] = value
    return values


def _first_param(
    params: dict[str, str],
    names: list[str],
) -> str | None:
    normalized = {key.casefold(): value for key, value in params.items()}
    for name in names:
        value = normalized.get(name.casefold())
        if value:
            return value
    return None


def _setting_names(
    settings: dict[str, object],
    key: str,
    defaults: list[str],
) -> list[str]:
    value = settings.get(key)
    if value is None:
        return defaults
    if not isinstance(value, list):
        raise ValueError(f"Heureka XML source settings.{key} must be an array.")
    return [str(item) for item in value]


def _availability(delivery_date: str | None) -> str:
    if delivery_date is None or not delivery_date.strip():
        return "limited"
    try:
        return "in_stock" if int(delivery_date) <= 3 else "limited"
    except ValueError:
        return "limited"


def _text(parent: ElementTree.Element, name: str) -> str | None:
    for child in parent:
        if _tag_name(child.tag) == name:
            value = (child.text or "").strip()
            return value or None
    return None


def _required_text(parent: ElementTree.Element, name: str) -> str:
    value = _text(parent, name)
    if value is None:
        raise ValueError(f"Heureka XML SHOPITEM is missing required element: {name}.")
    return value


def _required_float(parent: ElementTree.Element, name: str) -> float:
    value = _required_text(parent, name)
    return float(value.replace(" ", "").replace(",", "."))


def _tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _title_from_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-"))


def _timeout_seconds(source_config: SourceConfig) -> float:
    settings = source_config.settings or {}
    return float(settings.get("timeout_seconds", 30))
