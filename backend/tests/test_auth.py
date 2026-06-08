import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from app.core.config import settings


def build_init_data(bot_token: str, user: dict[str, object], auth_date: int | None = None) -> str:
    payload = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "test-query-id",
        "user": json.dumps(user, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(payload)


def test_telegram_auth_creates_user_and_allows_me(client: TestClient) -> None:
    init_data = build_init_data(
        "test-bot-token",
        {
            "id": 123456789,
            "username": "kupitest",
            "first_name": "Kupi",
            "last_name": "Tester",
            "language_code": "ru",
        },
    )

    auth_response = client.post("/v1/auth/telegram", json={"init_data": init_data})

    assert auth_response.status_code == 200
    auth_body = auth_response.json()
    assert auth_body["user"]["telegram_id"] == 123456789
    assert auth_body["user"]["username"] == "kupitest"
    assert auth_body["user"]["country"] == "CZ"
    assert auth_body["user"]["currency"] == "EUR"
    assert auth_body["tokens"]["token_type"] == "bearer"

    me_response = client.get(
        "/v1/me",
        headers={"Authorization": f"Bearer {auth_body['tokens']['access_token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["telegram_id"] == 123456789


def test_telegram_auth_rejects_user_outside_allowlist(client: TestClient) -> None:
    original_allowlist = settings.telegram_allowed_user_ids
    settings.telegram_allowed_user_ids = "123"
    try:
        init_data = build_init_data("test-bot-token", {"id": 999, "first_name": "Blocked"})

        response = client.post("/v1/auth/telegram", json={"init_data": init_data})
    finally:
        settings.telegram_allowed_user_ids = original_allowlist

    assert response.status_code == 403
    assert response.json()["detail"] == "Telegram user is not allowed for this environment."


def test_telegram_auth_allows_user_inside_allowlist(client: TestClient) -> None:
    original_allowlist = settings.telegram_allowed_user_ids
    settings.telegram_allowed_user_ids = "777"
    try:
        init_data = build_init_data("test-bot-token", {"id": 777, "first_name": "Allowed"})

        response = client.post("/v1/auth/telegram", json={"init_data": init_data})
    finally:
        settings.telegram_allowed_user_ids = original_allowlist

    assert response.status_code == 200
    assert response.json()["user"]["telegram_id"] == 777


def test_refresh_token_rotates_token_pair(client: TestClient) -> None:
    init_data = build_init_data("test-bot-token", {"id": 222, "first_name": "Refresh"})
    auth_response = client.post("/v1/auth/telegram", json={"init_data": init_data})
    refresh_token = auth_response.json()["tokens"]["refresh_token"]

    refresh_response = client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()
    assert refreshed["access_token"]
    assert refreshed["refresh_token"] != refresh_token

    old_token_response = client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert old_token_response.status_code == 401


def test_telegram_bot_user_auth_creates_user_and_token(client: TestClient) -> None:
    auth_response = client.post(
        "/v1/auth/telegram-bot-user",
        headers={"X-Telegram-Bot-Token": "test-bot-token"},
        json={
            "telegram_id": 444,
            "username": "botuser",
            "first_name": "Bot",
            "last_name": "User",
            "language": "ru",
        },
    )

    assert auth_response.status_code == 200
    auth_body = auth_response.json()
    assert auth_body["user"]["telegram_id"] == 444
    assert auth_body["user"]["username"] == "botuser"
    assert auth_body["tokens"]["access_token"]

    me_response = client.get(
        "/v1/me",
        headers={"Authorization": f"Bearer {auth_body['tokens']['access_token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["telegram_id"] == 444


def test_telegram_bot_user_auth_rejects_wrong_bot_token(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/telegram-bot-user",
        headers={"X-Telegram-Bot-Token": "wrong-token"},
        json={"telegram_id": 555, "first_name": "Nope"},
    )

    assert response.status_code == 401


def test_telegram_bot_user_auth_rejects_user_outside_allowlist(client: TestClient) -> None:
    original_allowlist = settings.telegram_allowed_user_ids
    settings.telegram_allowed_user_ids = "444"
    try:
        response = client.post(
            "/v1/auth/telegram-bot-user",
            headers={"X-Telegram-Bot-Token": "test-bot-token"},
            json={"telegram_id": 555, "first_name": "Blocked"},
        )
    finally:
        settings.telegram_allowed_user_ids = original_allowlist

    assert response.status_code == 403
    assert response.json()["detail"] == "Telegram user is not allowed for this environment."


def test_telegram_auth_rejects_invalid_hash(client: TestClient) -> None:
    init_data = build_init_data("wrong-token", {"id": 333, "first_name": "Nope"})

    response = client.post("/v1/auth/telegram", json={"init_data": init_data})

    assert response.status_code == 401
