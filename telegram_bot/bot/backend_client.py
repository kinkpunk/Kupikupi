from dataclasses import dataclass

import httpx


class BackendClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class ShoppingRequestResult:
    id: str
    status: str
    category: str | None
    size_value: str | None
    budget_amount: float | None
    display_currency: str | None


class BackendClient:
    def __init__(
        self,
        *,
        base_url: str,
        access_token: str | None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._access_token = access_token
        self._client = client

    async def create_shopping_request(self, text: str) -> ShoppingRequestResult:
        if not self._access_token:
            raise BackendClientError("Backend access token is not configured.")

        if self._client is None:
            async with httpx.AsyncClient(timeout=10) as client:
                return await self._create_shopping_request(client, text)
        return await self._create_shopping_request(self._client, text)

    async def _create_shopping_request(
        self,
        client: httpx.AsyncClient,
        text: str,
    ) -> ShoppingRequestResult:
        response = await client.post(
            f"{self._base_url}/shopping-requests",
            headers={"Authorization": f"Bearer {self._access_token}"},
            json={"text": text, "create_watchlist_after_confirmation": False},
        )
        if response.status_code >= 400:
            raise BackendClientError(f"Backend returned {response.status_code}.")
        payload = response.json()
        constraints = payload.get("constraints") or {}
        return ShoppingRequestResult(
            id=str(payload["id"]),
            status=str(payload["status"]),
            category=constraints.get("category"),
            size_value=constraints.get("size_value"),
            budget_amount=payload.get("budget_amount"),
            display_currency=payload.get("display_currency"),
        )
