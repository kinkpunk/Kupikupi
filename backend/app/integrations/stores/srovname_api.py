import os
import unicodedata
import uuid
from urllib.parse import urljoin

import httpx

from app.domains.stores.models import SourceConfig
from app.integrations.stores.base import SourceOfferRecord, SourceProductRecord, StoreSourceAdapter


class SrovnameApiSourceAdapter(StoreSourceAdapter):
    source_type = "srovname_api"

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
            raise ValueError("Srovname API source requires endpoint_url.")

        settings = self._source_config.settings or {}
        api_key = _api_key(settings)
        if not api_key:
            api_key_env = str(settings.get("api_key_env", "SROVNAME_API_KEY"))
            raise ValueError(f"Srovname API source requires {api_key_env}.")

        if self._client is None:
            async with httpx.AsyncClient(timeout=_timeout_seconds(settings)) as client:
                return await _fetch_records(client, self._source_config, api_key)
        return await _fetch_records(self._client, self._source_config, api_key)


async def _fetch_records(
    client: httpx.AsyncClient,
    source_config: SourceConfig,
    api_key: str,
) -> list[SourceOfferRecord]:
    settings = source_config.settings or {}
    items_per_page = int(settings.get("items_per_page", 100))
    max_pages = int(settings.get("max_pages", 10))
    page = int(settings.get("page_start", 1))
    endpoint_url = _products_endpoint(source_config.endpoint_url or "")
    records: list[SourceOfferRecord] = []

    for _ in range(max_pages):
        response = await client.get(
            endpoint_url,
            headers={"X-API-KEY": api_key},
            params={"page": page, "itemsPerPage": items_per_page},
        )
        response.raise_for_status()
        payload = response.json()
        products = _products_from_payload(payload)
        if not products:
            break
        records.extend(_record_from_product(product, settings) for product in products)
        if len(products) < items_per_page or _is_last_page(payload, page, items_per_page):
            break
        page += 1

    return records


def _products_endpoint(endpoint_url: str) -> str:
    if endpoint_url.rstrip("/").endswith("/eshop/products"):
        return endpoint_url
    return urljoin(endpoint_url.rstrip("/") + "/", "eshop/products")


def _products_from_payload(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        raise ValueError("Srovname API response must be an object.")
    products = payload.get("products")
    if not isinstance(products, list):
        raise ValueError("Srovname API response must include products list.")
    return [product for product in products if isinstance(product, dict)]


def _record_from_product(
    product: dict[str, object],
    settings: dict[str, object],
) -> SourceOfferRecord:
    price = _money(product.get("salePrice")) or _money(product.get("price"))
    old_price = _money(product.get("price"))
    if price is None:
        raise ValueError("Srovname product is missing price.value.")
    source_old_price = old_price[0] if old_price and old_price[0] > price[0] else None
    currency = price[1]
    category_name = _optional_str(product.get("productCategory")) or str(
        settings.get("default_category_name", "Unknown")
    )
    category_slug, mapped_category_name = _category_identity(category_name, settings)
    gtin = _optional_str(product.get("gtin"))
    product_id = _required_str(product, "id")

    return SourceOfferRecord(
        external_id=product_id,
        product_id=None,
        product_url=_required_str(product, "link"),
        source_price=price[0],
        source_old_price=source_old_price,
        source_currency=currency,
        eur_price=None,
        eur_old_price=None,
        fx_rate_to_eur=None,
        discount_percent=_discount_percent(price[0], source_old_price),
        availability=str(settings.get("default_availability", "in_stock")),
        sizes=[],
        product=SourceProductRecord(
            external_product_id=product_id,
            name=_required_str(product, "title"),
            category_slug=category_slug,
            category_name=mapped_category_name,
            brand_name=_optional_str(product.get("brand")),
            model=None,
            sku=gtin,
            image_url=_optional_str(product.get("imageLink")),
            attributes={
                "gtin": gtin,
                "google_product_category": product.get("googleProductCategory"),
                "condition": product.get("condition"),
                "source": "srovname.cz",
            },
        ),
    )


def _money(value: object) -> tuple[float, str] | None:
    if not isinstance(value, dict):
        return None
    amount = value.get("value")
    currency = value.get("currency")
    if amount is None or currency is None:
        return None
    return float(amount), str(currency).upper()


def _required_str(product: dict[str, object], key: str) -> str:
    value = _optional_str(product.get(key))
    if value is None:
        raise ValueError(f"Srovname product is missing {key}.")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _category_identity(category_name: str, settings: dict[str, object]) -> tuple[str, str]:
    category_map = settings.get("category_map")
    if isinstance(category_map, dict):
        mapped = category_map.get(category_name)
        if isinstance(mapped, dict):
            slug = mapped.get("slug")
            name = mapped.get("name")
            if slug:
                return str(slug), str(name or category_name)
        if isinstance(mapped, str) and mapped:
            return mapped, category_name
    return _slugify(category_name), category_name


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    chars = [char if char.isalnum() else "-" for char in ascii_text]
    slug = "-".join(part for part in "".join(chars).split("-") if part)
    return slug or "unknown"


def _discount_percent(price: float, old_price: float | None) -> float | None:
    if old_price is None or old_price <= 0 or price >= old_price:
        return None
    return round((old_price - price) / old_price * 100, 2)


def _is_last_page(payload: object, page: int, items_per_page: int) -> bool:
    if not isinstance(payload, dict):
        return True
    total_products = payload.get("totalProducts")
    if total_products is None:
        return False
    return page * items_per_page >= int(total_products)


def _api_key(settings: dict[str, object]) -> str | None:
    api_key_env = str(settings.get("api_key_env", "SROVNAME_API_KEY"))
    return _optional_str(os.environ.get(api_key_env))


def _timeout_seconds(settings: dict[str, object]) -> float:
    value = settings.get("timeout_seconds", 30)
    return float(value)
