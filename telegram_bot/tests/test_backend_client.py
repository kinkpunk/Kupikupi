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
