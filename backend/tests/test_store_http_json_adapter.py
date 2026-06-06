import httpx

from app.domains.stores.models import SourceConfig
from app.integrations.stores.http_json import HttpJsonSourceAdapter
from app.integrations.stores.registry import adapter_from_source_config


async def test_http_json_adapter_fetches_records_from_wrapped_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://feeds.example.test/offers.json"
        return httpx.Response(
            200,
            json={
                "records": [
                    {
                        "external_id": "feed-1",
                        "product_url": "https://shop.example.test/item-1",
                        "source_price": 100,
                        "source_currency": "EUR",
                        "eur_price": 100,
                        "availability": "in_stock",
                    }
                ]
            },
        )

    source_config = SourceConfig(
        source_type="http_json",
        endpoint_url="https://feeds.example.test/offers.json",
        active=True,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        records = await HttpJsonSourceAdapter(source_config, client=client).fetch_offers()

    assert len(records) == 1
    assert records[0].external_id == "feed-1"
    assert records[0].source_currency == "EUR"


async def test_http_json_adapter_accepts_top_level_record_array() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "external_id": "feed-array-1",
                    "product_url": "https://shop.example.test/item-array-1",
                    "source_price": 1250,
                    "source_currency": "CZK",
                    "availability": "in_stock",
                }
            ],
        )

    source_config = SourceConfig(
        source_type="http_json",
        endpoint_url="https://feeds.example.test/offers-array.json",
        active=True,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        records = await HttpJsonSourceAdapter(source_config, client=client).fetch_offers()

    assert records[0].external_id == "feed-array-1"
    assert records[0].eur_price is None


def test_registry_returns_http_json_adapter() -> None:
    source_config = SourceConfig(
        source_type="http_json",
        endpoint_url="https://feeds.example.test/offers.json",
        active=True,
    )

    adapter = adapter_from_source_config(source_config)

    assert isinstance(adapter, HttpJsonSourceAdapter)
