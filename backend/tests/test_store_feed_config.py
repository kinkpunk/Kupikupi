import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.domains.stores.feed_config import (
    StoreFeedConfig,
    store_feed_template,
    upsert_store_feed_config,
)
from app.domains.stores.models import SourceConfig, Store


async def test_upsert_store_feed_config_creates_store_and_source_config(db_session_factory) -> None:
    payload = _feed_payload()

    async with db_session_factory() as session:
        result = await upsert_store_feed_config(session, payload)
        await session.commit()

    assert result.created_store is True
    assert result.created_source_config is True
    assert result.store.name == "Example Store"
    assert result.source_config.source_type == "http_csv"
    assert result.source_config.sync_interval_minutes == 360

    async with db_session_factory() as session:
        assert await session.scalar(select(func.count(Store.id))) == 1
        assert await session.scalar(select(func.count(SourceConfig.id))) == 1


async def test_upsert_store_feed_config_updates_existing_feed(db_session_factory) -> None:
    payload = _feed_payload()

    async with db_session_factory() as session:
        first = await upsert_store_feed_config(session, payload)
        await session.commit()
        store_id = first.store.id
        source_config_id = first.source_config.id

    updated_payload = _feed_payload(
        {
            "store": {
                "name": "Example Store",
                "country": "cz",
                "url": "https://www.example.test/new",
                "active": False,
                "delivers_to_cz": False,
            },
            "source": {
                **store_feed_template()["source"],
                "endpoint_url": "https://feeds.example.test/offers.csv",
                "sync_interval_minutes": 720,
                "settings": {
                    **store_feed_template()["source"]["settings"],
                    "timeout_seconds": 20,
                },
            },
        }
    )

    async with db_session_factory() as session:
        result = await upsert_store_feed_config(session, updated_payload)
        await session.commit()

    assert result.created_store is False
    assert result.created_source_config is False
    assert result.store.id == store_id
    assert result.source_config.id == source_config_id
    assert result.store.country == "CZ"
    assert result.store.active is False
    assert result.source_config.sync_interval_minutes == 720
    assert result.source_config.settings["timeout_seconds"] == 20

    async with db_session_factory() as session:
        assert await session.scalar(select(func.count(Store.id))) == 1
        assert await session.scalar(select(func.count(SourceConfig.id))) == 1


def test_store_feed_template_is_valid() -> None:
    payload = StoreFeedConfig.model_validate(store_feed_template())

    assert payload.source.source_type == "http_csv"


def test_store_feed_config_rejects_unsupported_source_type() -> None:
    data = store_feed_template()
    data["source"]["source_type"] = "scraper"

    with pytest.raises(ValidationError, match="source.source_type"):
        StoreFeedConfig.model_validate(data)


def test_store_feed_config_rejects_http_csv_without_required_columns() -> None:
    data = store_feed_template()
    data["source"]["settings"]["columns"] = {"external_id": "id"}

    with pytest.raises(ValidationError, match="product_name"):
        StoreFeedConfig.model_validate(data)


def _feed_payload(overrides: dict | None = None) -> StoreFeedConfig:
    data = store_feed_template()
    if overrides:
        data.update(overrides)
    return StoreFeedConfig.model_validate(data)
