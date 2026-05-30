import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl


class TelegramAuthError(ValueError):
    pass


@dataclass(frozen=True)
class TelegramUserData:
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language: str | None


def validate_telegram_init_data(
    init_data: str,
    *,
    bot_token: str,
    max_age: timedelta = timedelta(days=1),
) -> TelegramUserData:
    parsed = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = parsed.pop("hash", None)
    auth_date_raw = parsed.get("auth_date")
    user_raw = parsed.get("user")

    if not received_hash or not auth_date_raw or not user_raw:
        raise TelegramAuthError("Telegram init data is missing required fields.")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise TelegramAuthError("Telegram init data hash is invalid.")

    try:
        auth_date = datetime.fromtimestamp(int(auth_date_raw), tz=UTC)
    except ValueError as exc:
        raise TelegramAuthError("Telegram auth_date is invalid.") from exc

    if datetime.now(UTC) - auth_date > max_age:
        raise TelegramAuthError("Telegram init data is expired.")

    try:
        user = json.loads(user_raw)
        telegram_id = int(user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise TelegramAuthError("Telegram user payload is invalid.") from exc

    return TelegramUserData(
        telegram_id=telegram_id,
        username=user.get("username"),
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        language=user.get("language_code"),
    )

