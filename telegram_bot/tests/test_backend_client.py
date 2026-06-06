import httpx
import pytest

from bot.backend_client import BackendClient, BackendClientError


@pytest.mark.asyncio
async def test_backend_client_creates_shopping_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.example.test/v1/shopping-requests"
        assert request.headers["Authorization"] == "Bearer token"
        return httpx.Response(
            201,
            json={
                "id": "request-1",
                "status": "parsed",
                "budget_amount": 150,
                "display_currency": "EUR",
                "constraints": {
                    "category": "running-shoes",
                    "size_value": "41",
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = BackendClient(
            base_url="https://api.example.test/v1",
            access_token="token",
            client=http_client,
        )
        result = await client.create_shopping_request("Хочу кроссовки")

    assert result.id == "request-1"
    assert result.status == "parsed"
    assert result.category == "running-shoes"
    assert result.size_value == "41"
    assert result.budget_amount == 150
    assert result.display_currency == "EUR"


@pytest.mark.asyncio
async def test_backend_client_requires_access_token() -> None:
    client = BackendClient(base_url="https://api.example.test/v1", access_token=None)

    with pytest.raises(BackendClientError, match="access token"):
        await client.create_shopping_request("Хочу кроссовки")


@pytest.mark.asyncio
async def test_backend_client_raises_for_backend_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Unauthorized"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = BackendClient(
            base_url="https://api.example.test/v1",
            access_token="bad-token",
            client=http_client,
        )
        with pytest.raises(BackendClientError, match="401"):
            await client.create_shopping_request("Хочу кроссовки")


@pytest.mark.asyncio
async def test_backend_client_lists_shopping_requests() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/shopping-requests"
        assert dict(request.url.params) == {"limit": "5", "offset": "0"}
        assert request.headers["Authorization"] == "Bearer token"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "request-1",
                        "raw_text": "Хочу беговые кроссовки. Размер 41.",
                        "status": "parsed",
                        "budget_amount": 150,
                        "display_currency": "EUR",
                        "constraints": {
                            "category": "running-shoes",
                            "size_value": "41",
                        },
                    },
                ],
                "limit": 5,
                "offset": 0,
                "total": 1,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = BackendClient(
            base_url="https://api.example.test/v1",
            access_token="token",
            client=http_client,
        )
        result = await client.list_shopping_requests()

    assert len(result) == 1
    assert result[0].id == "request-1"
    assert result[0].raw_text == "Хочу беговые кроссовки. Размер 41."
    assert result[0].category == "running-shoes"
    assert result[0].size_value == "41"
    assert result[0].budget_amount == 150


@pytest.mark.asyncio
async def test_backend_client_lists_watchlists() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/watchlists"
        assert dict(request.url.params) == {
            "limit": "5",
            "offset": "0",
            "archived": "false",
        }
        assert request.headers["Authorization"] == "Bearer token"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "watchlist-1",
                        "type": "product_search",
                        "active": True,
                        "archived": False,
                        "model": "Nike Pegasus",
                        "category": "running-shoes",
                        "size_value": "41",
                        "target_price": 150,
                        "target_price_currency": "EUR",
                    },
                ],
                "limit": 5,
                "offset": 0,
                "total": 1,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = BackendClient(
            base_url="https://api.example.test/v1",
            access_token="token",
            client=http_client,
        )
        result = await client.list_watchlists()

    assert len(result) == 1
    assert result[0].id == "watchlist-1"
    assert result[0].model == "Nike Pegasus"
    assert result[0].category == "running-shoes"
    assert result[0].size_value == "41"
    assert result[0].target_price == 150
