from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.stores.models import SourceConfig, Store

SUPPORTED_FEED_SOURCE_TYPES = {"heureka_xml", "http_csv", "http_json"}
REQUIRED_HTTP_CSV_COLUMNS = {"external_id", "product_url", "source_price", "product_name"}


class StoreFeedConfig(BaseModel):
    store: "StoreFeedStoreConfig"
    source: "StoreFeedSourceConfig"


class StoreFeedStoreConfig(BaseModel):
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    country: str = Field(default="CZ", min_length=2, max_length=2)
    active: bool = True
    delivers_to_cz: bool = True

    @model_validator(mode="after")
    def validate_store_url(self) -> "StoreFeedStoreConfig":
        _validate_http_url(self.url, field_name="store.url")
        self.country = self.country.upper()
        return self


class StoreFeedSourceConfig(BaseModel):
    source_type: str
    endpoint_url: str = Field(min_length=1)
    active: bool = True
    sync_interval_minutes: int | None = Field(default=360, ge=1)
    settings: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_source(self) -> "StoreFeedSourceConfig":
        if self.source_type not in SUPPORTED_FEED_SOURCE_TYPES:
            supported = ", ".join(sorted(SUPPORTED_FEED_SOURCE_TYPES))
            raise ValueError(f"source.source_type must be one of: {supported}.")
        _validate_http_url(self.endpoint_url, field_name="source.endpoint_url")
        if self.source_type == "http_csv":
            _validate_http_csv_settings(self.settings)
        if self.source_type == "heureka_xml":
            _validate_heureka_xml_settings(self.settings)
        return self


@dataclass(frozen=True)
class StoreFeedConfigResult:
    store: Store
    source_config: SourceConfig
    created_store: bool
    created_source_config: bool


async def upsert_store_feed_config(
    session: AsyncSession,
    payload: StoreFeedConfig,
) -> StoreFeedConfigResult:
    store = await _get_store_by_name(session, payload.store.name)
    created_store = store is None
    if store is None:
        store = Store(
            name=payload.store.name,
            country=payload.store.country,
            url=payload.store.url,
            active=payload.store.active,
            delivers_to_cz=payload.store.delivers_to_cz,
        )
        session.add(store)
        await session.flush()
    else:
        store.country = payload.store.country
        store.url = payload.store.url
        store.active = payload.store.active
        store.delivers_to_cz = payload.store.delivers_to_cz

    source_config = await _get_source_config(
        session,
        store_id=store.id,
        source_type=payload.source.source_type,
        endpoint_url=payload.source.endpoint_url,
    )
    created_source_config = source_config is None
    if source_config is None:
        source_config = SourceConfig(
            store_id=store.id,
            source_type=payload.source.source_type,
            endpoint_url=payload.source.endpoint_url,
            active=payload.source.active,
            sync_interval_minutes=payload.source.sync_interval_minutes,
            settings=payload.source.settings,
        )
        session.add(source_config)
    else:
        source_config.active = payload.source.active
        source_config.sync_interval_minutes = payload.source.sync_interval_minutes
        source_config.settings = payload.source.settings

    await session.flush()
    return StoreFeedConfigResult(
        store=store,
        source_config=source_config,
        created_store=created_store,
        created_source_config=created_source_config,
    )


def store_feed_template() -> dict[str, Any]:
    return {
        "store": {
            "name": "Example Store",
            "country": "CZ",
            "url": "https://www.example.test",
            "active": True,
            "delivers_to_cz": True,
        },
        "source": {
            "source_type": "http_csv",
            "endpoint_url": "https://feeds.example.test/offers.csv",
            "active": True,
            "sync_interval_minutes": 360,
            "settings": {
                "delimiter": ",",
                "size_delimiter": "|",
                "columns": {
                    "external_id": "id",
                    "product_url": "url",
                    "source_price": "price",
                    "source_old_price": "old_price",
                    "source_currency": "currency",
                    "product_name": "name",
                    "brand_name": "brand",
                    "category_slug": "category",
                    "category_name": "category_name",
                    "model": "model",
                    "sku": "sku",
                    "image_url": "image_url",
                    "sizes": "sizes",
                },
                "defaults": {
                    "source_currency": "CZK",
                    "availability": "in_stock",
                    "size_system": "EU",
                },
            },
        },
    }


def heureka_xml_feed_template() -> dict[str, Any]:
    return {
        "store": {
            "name": "Example Heureka Store",
            "country": "CZ",
            "url": "https://www.example.test",
            "active": True,
            "delivers_to_cz": True,
        },
        "source": {
            "source_type": "heureka_xml",
            "endpoint_url": "https://www.example.test/heureka.xml",
            "active": True,
            "sync_interval_minutes": 120,
            "settings": {
                "source_currency": "CZK",
                "size_system": "EU",
                "size_param_names": ["Velikost", "Size"],
                "color_param_names": ["Barva", "Color"],
                "category_map": {
                    "Bezecke boty": {
                        "slug": "running-shoes",
                        "name": "Running Shoes",
                    },
                    "Tenisky": {
                        "slug": "sneakers",
                        "name": "Sneakers",
                    },
                },
            },
        },
    }


async def _get_store_by_name(session: AsyncSession, name: str) -> Store | None:
    result = await session.execute(select(Store).where(Store.name == name))
    return result.scalar_one_or_none()


async def _get_source_config(
    session: AsyncSession,
    *,
    store_id,
    source_type: str,
    endpoint_url: str,
) -> SourceConfig | None:
    result = await session.execute(
        select(SourceConfig).where(
            SourceConfig.store_id == store_id,
            SourceConfig.source_type == source_type,
            SourceConfig.endpoint_url == endpoint_url,
        )
    )
    return result.scalar_one_or_none()


def _validate_http_csv_settings(settings: dict[str, Any]) -> None:
    columns = settings.get("columns")
    if not isinstance(columns, dict):
        raise ValueError("source.settings.columns must be an object for http_csv feeds.")
    missing_columns = sorted(REQUIRED_HTTP_CSV_COLUMNS - set(columns))
    if missing_columns:
        raise ValueError(
            "source.settings.columns is missing required logical columns: "
            + ", ".join(missing_columns)
            + "."
        )


def _validate_heureka_xml_settings(settings: dict[str, Any]) -> None:
    category_map = settings.get("category_map")
    if not isinstance(category_map, dict) or not category_map:
        raise ValueError("source.settings.category_map must be a non-empty object.")


def _validate_http_url(value: str, *, field_name: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be an absolute http(s) URL.")
