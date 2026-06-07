from datetime import UTC, datetime

import httpx
from sqlalchemy import select

from app.domains.fx.models import FxRate
from app.domains.offers.models import Offer
from app.domains.stores.models import SourceConfig, Store
from app.domains.stores.sync import run_source_sync
from app.integrations.stores.http_csv import HttpCsvSourceAdapter
from app.integrations.stores.registry import adapter_from_source_config


async def test_http_csv_adapter_fetches_records_with_column_mapping() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://feeds.example.test/offers.csv"
        return httpx.Response(
            200,
            text=(
                "id,url,price,old_price,currency,name,brand,category,model,sku,sizes\n"
                "feed-1,https://shop.example.test/item-1,3290,4490,CZK,"
                "New Balance Fresh Foam 1080,New Balance,running-shoes,"
                "Fresh Foam 1080,NB-1080,41|42\n"
            ),
        )

    source_config = SourceConfig(
        source_type="http_csv",
        endpoint_url="https://feeds.example.test/offers.csv",
        active=True,
        settings={
            "columns": {
                "external_id": "id",
                "product_url": "url",
                "source_price": "price",
                "source_old_price": "old_price",
                "source_currency": "currency",
                "product_name": "name",
                "brand_name": "brand",
                "category_slug": "category",
                "model": "model",
                "sku": "sku",
                "sizes": "sizes",
            }
        },
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        records = await HttpCsvSourceAdapter(source_config, client=client).fetch_offers()

    assert len(records) == 1
    assert records[0].external_id == "feed-1"
    assert records[0].source_price == 3290
    assert records[0].source_currency == "CZK"
    assert records[0].product is not None
    assert records[0].product.name == "New Balance Fresh Foam 1080"
    assert records[0].product.category_slug == "running-shoes"
    assert records[0].sizes == [
        {"size_value": "41", "size_system": "EU", "in_stock": True},
        {"size_value": "42", "size_system": "EU", "in_stock": True},
    ]


def test_registry_returns_http_csv_adapter() -> None:
    source_config = SourceConfig(
        source_type="http_csv",
        endpoint_url="https://feeds.example.test/offers.csv",
        active=True,
    )

    adapter = adapter_from_source_config(source_config)

    assert isinstance(adapter, HttpCsvSourceAdapter)


async def test_http_csv_source_config_sync_imports_products_and_offers(db_session_factory) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=(
                "external_id,product_url,source_price,source_currency,product_name,brand_name,"
                "category_slug,category_name,model,sku,sizes\n"
                "csv-nb-1080,https://shop.example.test/nb-1080,3290,CZK,"
                "New Balance Fresh Foam 1080,New Balance,running-shoes,Running Shoes,"
                "Fresh Foam 1080,CSV-NB-1080,41|42\n"
            ),
        )

    async with db_session_factory() as session:
        store = Store(name="CSV Store", country="CZ", url="https://shop.example.test")
        source_config = SourceConfig(
            store=store,
            source_type="http_csv",
            endpoint_url="https://feeds.example.test/offers.csv",
            active=True,
        )
        session.add_all(
            [
                store,
                    source_config,
                    FxRate(
                        currency="CZK",
                        rate_to_eur=0.040817,
                        source="test",
                        valid_at=datetime(2026, 6, 7, tzinfo=UTC),
                    ),
            ]
        )
        await session.flush()

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = HttpCsvSourceAdapter(source_config, client=client)
            sync_run = await run_source_sync(
                session,
                adapter=adapter,
                store_id=store.id,
                source_config_id=source_config.id,
            )
        await session.commit()

        offer = await session.scalar(select(Offer).where(Offer.external_id == "csv-nb-1080"))

    assert sync_run.status == "succeeded"
    assert sync_run.products_seen == 1
    assert sync_run.offers_seen == 1
    assert offer is not None
    assert float(offer.eur_price) == 134.29
