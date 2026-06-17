import httpx
import pytest

from app.domains.stores.models import SourceConfig
from app.integrations.stores.registry import adapter_from_source_config
from app.integrations.stores.srovname_api import SrovnameApiSourceAdapter


async def test_srovname_api_adapter_fetches_products_with_api_key_header(monkeypatch) -> None:
    monkeypatch.setenv("SROVNAME_API_KEY", "test-api-key")
    requested_pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-API-KEY"] == "test-api-key"
        assert str(request.url).startswith("https://rest.srovname.cz/api/v1/eshop/products?")
        page = int(request.url.params["page"])
        requested_pages.append(page)
        if page == 1:
            return httpx.Response(
                200,
                json={
                    "totalProducts": 2,
                    "itemsPerPage": 1,
                    "page": 1,
                    "products": [
                        {
                            "id": "sr-1",
                            "title": "New Balance Fresh Foam 1080",
                            "link": "https://shop.example.test/nb-1080",
                            "imageLink": "https://shop.example.test/nb-1080.jpg",
                            "price": {"value": 3290, "currency": "CZK"},
                            "salePrice": {"value": 2990, "currency": "CZK"},
                            "brand": "New Balance",
                            "productCategory": "Bezecke boty",
                            "googleProductCategory": 187,
                            "condition": "new",
                            "gtin": "1234567890123",
                        }
                    ],
                },
            )
        return httpx.Response(
            200,
            json={
                "totalProducts": 2,
                "itemsPerPage": 1,
                "page": 2,
                "products": [
                    {
                        "id": "sr-2",
                        "title": "Nike Pegasus 41",
                        "link": "https://shop.example.test/pegasus-41",
                        "price": {"value": 2790, "currency": "CZK"},
                        "brand": "Nike",
                        "productCategory": "Running Shoes",
                    }
                ],
            },
        )

    source_config = SourceConfig(
        source_type="srovname_api",
        endpoint_url="https://rest.srovname.cz/api/v1/",
        active=True,
        settings={
            "items_per_page": 1,
            "max_pages": 5,
            "category_map": {"Bezecke boty": {"slug": "running-shoes", "name": "Running Shoes"}},
        },
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        records = await SrovnameApiSourceAdapter(source_config, client=client).fetch_offers()

    assert requested_pages == [1, 2]
    assert len(records) == 2
    assert records[0].external_id == "sr-1"
    assert records[0].product_url == "https://shop.example.test/nb-1080"
    assert records[0].source_price == 2990
    assert records[0].source_old_price == 3290
    assert records[0].source_currency == "CZK"
    assert records[0].discount_percent == 9.12
    assert records[0].product is not None
    assert records[0].product.category_slug == "running-shoes"
    assert records[0].product.category_name == "Running Shoes"
    assert records[0].product.brand_name == "New Balance"
    assert records[0].product.sku == "1234567890123"
    assert records[0].product.attributes == {
        "gtin": "1234567890123",
        "google_product_category": 187,
        "condition": "new",
        "source": "srovname.cz",
    }
    assert records[1].source_old_price is None
    assert records[1].product is not None
    assert records[1].product.sku is None
    assert records[1].product.attributes["gtin"] is None
    assert records[1].product.category_slug == "running-shoes"


async def test_srovname_api_adapter_accepts_full_products_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("CUSTOM_SROVNAME_KEY", "custom-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith("https://rest.srovname.cz/api/v1/eshop/products?")
        assert request.headers["X-API-KEY"] == "custom-key"
        return httpx.Response(200, json={"totalProducts": 0, "products": []})

    source_config = SourceConfig(
        source_type="srovname_api",
        endpoint_url="https://rest.srovname.cz/api/v1/eshop/products",
        active=True,
        settings={"api_key_env": "CUSTOM_SROVNAME_KEY"},
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        records = await SrovnameApiSourceAdapter(source_config, client=client).fetch_offers()

    assert records == []


async def test_srovname_api_adapter_handles_empty_products(monkeypatch) -> None:
    monkeypatch.setenv("SROVNAME_API_KEY", "test-api-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"totalProducts": 0, "products": []})

    source_config = SourceConfig(
        source_type="srovname_api",
        endpoint_url="https://rest.srovname.cz/api/v1/",
        active=True,
        settings={"items_per_page": 50},
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        records = await SrovnameApiSourceAdapter(source_config, client=client).fetch_offers()

    assert records == []


async def test_srovname_api_adapter_falls_back_when_sale_price_is_null(monkeypatch) -> None:
    monkeypatch.setenv("SROVNAME_API_KEY", "test-api-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "totalProducts": 1,
                "products": [
                    {
                        "id": "sr-null-sale",
                        "title": "Adidas Ultraboost",
                        "link": "https://shop.example.test/ultraboost",
                        "price": {"value": 159.99, "currency": "eur"},
                        "salePrice": None,
                        "brand": "Adidas",
                        "productCategory": "Running Shoes",
                    }
                ],
            },
        )

    source_config = SourceConfig(
        source_type="srovname_api",
        endpoint_url="https://rest.srovname.cz/api/v1/",
        active=True,
        settings={},
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        records = await SrovnameApiSourceAdapter(source_config, client=client).fetch_offers()

    assert records[0].source_price == 159.99
    assert records[0].source_old_price is None
    assert records[0].source_currency == "EUR"
    assert records[0].discount_percent is None


async def test_srovname_api_adapter_preserves_zero_sale_price(monkeypatch) -> None:
    monkeypatch.setenv("SROVNAME_API_KEY", "test-api-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "totalProducts": 1,
                "products": [
                    {
                        "id": "sr-zero-sale",
                        "title": "Clearance Running Shoes",
                        "link": "https://shop.example.test/clearance",
                        "price": {"value": 100, "currency": "CZK"},
                        "salePrice": {"value": 0, "currency": "CZK"},
                        "productCategory": "Running Shoes",
                    }
                ],
            },
        )

    source_config = SourceConfig(
        source_type="srovname_api",
        endpoint_url="https://rest.srovname.cz/api/v1/",
        active=True,
        settings={},
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        records = await SrovnameApiSourceAdapter(source_config, client=client).fetch_offers()

    assert records[0].source_price == 0
    assert records[0].source_old_price == 100
    assert records[0].discount_percent == 100


async def test_srovname_api_adapter_raises_for_api_errors(monkeypatch) -> None:
    monkeypatch.setenv("SROVNAME_API_KEY", "test-api-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "invalid api key"}, request=request)

    source_config = SourceConfig(
        source_type="srovname_api",
        endpoint_url="https://rest.srovname.cz/api/v1/",
        active=True,
        settings={},
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await SrovnameApiSourceAdapter(source_config, client=client).fetch_offers()


async def test_srovname_api_adapter_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("SROVNAME_API_KEY", raising=False)
    source_config = SourceConfig(
        source_type="srovname_api",
        endpoint_url="https://rest.srovname.cz/api/v1/",
        active=True,
        settings={},
    )

    try:
        await SrovnameApiSourceAdapter(source_config).fetch_offers()
    except ValueError as exc:
        assert "SROVNAME_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected missing API key error.")


def test_registry_returns_srovname_api_adapter() -> None:
    source_config = SourceConfig(
        source_type="srovname_api",
        endpoint_url="https://rest.srovname.cz/api/v1/",
        active=True,
        settings={"api_key_env": "SROVNAME_API_KEY"},
    )

    adapter = adapter_from_source_config(source_config)

    assert isinstance(adapter, SrovnameApiSourceAdapter)
