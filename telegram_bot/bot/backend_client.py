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


@dataclass(frozen=True)
class ShoppingRequestSummary:
    id: str
    raw_text: str
    status: str
    category: str | None
    size_value: str | None
    budget_amount: float | None
    display_currency: str | None


@dataclass(frozen=True)
class WatchlistSummary:
    id: str
    type: str
    active: bool
    archived: bool
    model: str | None
    category: str | None
    size_value: str | None
    target_price: float | None
    target_price_currency: str | None


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

    async def list_shopping_requests(self, *, limit: int = 5) -> list[ShoppingRequestSummary]:
        self._ensure_access_token()
        if self._client is None:
            async with httpx.AsyncClient(timeout=10) as client:
                return await self._list_shopping_requests(client, limit=limit)
        return await self._list_shopping_requests(self._client, limit=limit)

    async def list_watchlists(self, *, limit: int = 5) -> list[WatchlistSummary]:
        self._ensure_access_token()
        if self._client is None:
            async with httpx.AsyncClient(timeout=10) as client:
                return await self._list_watchlists(client, limit=limit)
        return await self._list_watchlists(self._client, limit=limit)

    async def pause_watchlist(self, watchlist_id: str) -> WatchlistSummary:
        self._ensure_access_token()
        if self._client is None:
            async with httpx.AsyncClient(timeout=10) as client:
                return await self._post_watchlist_action(client, watchlist_id, "pause")
        return await self._post_watchlist_action(self._client, watchlist_id, "pause")

    async def archive_watchlist(self, watchlist_id: str) -> WatchlistSummary:
        self._ensure_access_token()
        if self._client is None:
            async with httpx.AsyncClient(timeout=10) as client:
                return await self._post_watchlist_action(client, watchlist_id, "archive")
        return await self._post_watchlist_action(self._client, watchlist_id, "archive")

    async def resume_watchlist(self, watchlist_id: str) -> WatchlistSummary:
        self._ensure_access_token()
        if self._client is None:
            async with httpx.AsyncClient(timeout=10) as client:
                return await self._resume_watchlist(client, watchlist_id)
        return await self._resume_watchlist(self._client, watchlist_id)

    def _ensure_access_token(self) -> None:
        if not self._access_token:
            raise BackendClientError("Backend access token is not configured.")

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

    async def _list_shopping_requests(
        self,
        client: httpx.AsyncClient,
        *,
        limit: int,
    ) -> list[ShoppingRequestSummary]:
        response = await client.get(
            f"{self._base_url}/shopping-requests",
            headers={"Authorization": f"Bearer {self._access_token}"},
            params={"limit": limit, "offset": 0},
        )
        if response.status_code >= 400:
            raise BackendClientError(f"Backend returned {response.status_code}.")
        payload = response.json()
        return [_shopping_request_summary_from_payload(item) for item in payload.get("items", [])]

    async def _list_watchlists(
        self,
        client: httpx.AsyncClient,
        *,
        limit: int,
    ) -> list[WatchlistSummary]:
        response = await client.get(
            f"{self._base_url}/watchlists",
            headers={"Authorization": f"Bearer {self._access_token}"},
            params={"limit": limit, "offset": 0, "archived": False},
        )
        if response.status_code >= 400:
            raise BackendClientError(f"Backend returned {response.status_code}.")
        payload = response.json()
        return [_watchlist_summary_from_payload(item) for item in payload.get("items", [])]

    async def _post_watchlist_action(
        self,
        client: httpx.AsyncClient,
        watchlist_id: str,
        action: str,
    ) -> WatchlistSummary:
        response = await client.post(
            f"{self._base_url}/watchlists/{watchlist_id}/{action}",
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        if response.status_code >= 400:
            raise BackendClientError(f"Backend returned {response.status_code}.")
        return _watchlist_summary_from_payload(response.json())

    async def _resume_watchlist(
        self,
        client: httpx.AsyncClient,
        watchlist_id: str,
    ) -> WatchlistSummary:
        response = await client.put(
            f"{self._base_url}/watchlists/{watchlist_id}",
            headers={"Authorization": f"Bearer {self._access_token}"},
            json={"active": True, "archived": False},
        )
        if response.status_code >= 400:
            raise BackendClientError(f"Backend returned {response.status_code}.")
        return _watchlist_summary_from_payload(response.json())


def _shopping_request_summary_from_payload(payload: dict[str, object]) -> ShoppingRequestSummary:
    constraints = payload.get("constraints") or {}
    if not isinstance(constraints, dict):
        constraints = {}
    return ShoppingRequestSummary(
        id=str(payload["id"]),
        raw_text=str(payload["raw_text"]),
        status=str(payload["status"]),
        category=_optional_str(constraints.get("category")),
        size_value=_optional_str(constraints.get("size_value")),
        budget_amount=_optional_float(payload.get("budget_amount")),
        display_currency=_optional_str(payload.get("display_currency")),
    )


def _watchlist_summary_from_payload(payload: dict[str, object]) -> WatchlistSummary:
    return WatchlistSummary(
        id=str(payload["id"]),
        type=str(payload["type"]),
        active=bool(payload["active"]),
        archived=bool(payload["archived"]),
        model=_optional_str(payload.get("model")),
        category=_optional_str(payload.get("category")),
        size_value=_optional_str(payload.get("size_value")),
        target_price=_optional_float(payload.get("target_price")),
        target_price_currency=_optional_str(payload.get("target_price_currency")),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)
