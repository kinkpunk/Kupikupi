import httpx
import pytest

from bot.backend_client import BackendClient, BackendClientError, TelegramUserIdentity


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
async def test_backend_client_authenticates_telegram_bot_user() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/auth/telegram-bot-user"
        assert request.headers["X-Telegram-Bot-Token"] == "bot-token"
        assert request.content == (
            b'{"telegram_id":123,"username":"runner","first_name":"Run",'
            b'"last_name":"Tester","language":"ru"}'
        )
        return httpx.Response(
            200,
            json={
                "user": {"id": "user-1", "telegram_id": 123},
                "tokens": {
                    "access_token": "user-access-token",
                    "refresh_token": "refresh-token",
                    "token_type": "bearer",
                    "expires_in": 900,
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = BackendClient(
            base_url="https://api.example.test/v1",
            access_token=None,
            client=http_client,
        )
        access_token = await client.authenticate_telegram_bot_user(
            bot_token="bot-token",
            user=TelegramUserIdentity(
                telegram_id=123,
                username="runner",
                first_name="Run",
                last_name="Tester",
                language="ru",
            ),
        )

    assert access_token == "user-access-token"


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


@pytest.mark.asyncio
async def test_backend_client_pauses_watchlist() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/watchlists/watchlist-1/pause"
        assert request.headers["Authorization"] == "Bearer token"
        return httpx.Response(200, json=_watchlist_payload(active=False, archived=False))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = BackendClient(
            base_url="https://api.example.test/v1",
            access_token="token",
            client=http_client,
        )
        result = await client.pause_watchlist("watchlist-1")

    assert result.id == "watchlist-1"
    assert result.active is False
    assert result.archived is False


@pytest.mark.asyncio
async def test_backend_client_archives_watchlist() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/watchlists/watchlist-1/archive"
        assert request.headers["Authorization"] == "Bearer token"
        return httpx.Response(200, json=_watchlist_payload(active=False, archived=True))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = BackendClient(
            base_url="https://api.example.test/v1",
            access_token="token",
            client=http_client,
        )
        result = await client.archive_watchlist("watchlist-1")

    assert result.id == "watchlist-1"
    assert result.active is False
    assert result.archived is True


@pytest.mark.asyncio
async def test_backend_client_resumes_watchlist() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        assert request.url.path == "/v1/watchlists/watchlist-1"
        assert request.headers["Authorization"] == "Bearer token"
        assert request.content == b'{"active":true,"archived":false}'
        return httpx.Response(200, json=_watchlist_payload(active=True, archived=False))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = BackendClient(
            base_url="https://api.example.test/v1",
            access_token="token",
            client=http_client,
        )
        result = await client.resume_watchlist("watchlist-1")

    assert result.id == "watchlist-1"
    assert result.active is True
    assert result.archived is False


def _watchlist_payload(*, active: bool, archived: bool) -> dict[str, object]:
    return {
        "id": "watchlist-1",
        "type": "agent_request",
        "active": active,
        "archived": archived,
        "model": "Nike Pegasus",
        "category": "running-shoes",
        "size_value": "41",
        "target_price": 150,
        "target_price_currency": "EUR",
    }
