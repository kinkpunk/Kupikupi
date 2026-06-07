from bot.config import BotSettings


def test_runtime_configuration_requires_telegram_token() -> None:
    settings = BotSettings(telegram_bot_token="", backend_api_url="http://backend:8000/v1")

    assert settings.validate_runtime_configuration() == ["TELEGRAM_BOT_TOKEN is required."]


def test_runtime_configuration_requires_absolute_backend_url() -> None:
    settings = BotSettings(telegram_bot_token="token", backend_api_url="/v1")

    assert settings.validate_runtime_configuration() == [
        "BACKEND_API_URL must be an absolute http(s) URL."
    ]


def test_runtime_configuration_accepts_valid_settings() -> None:
    settings = BotSettings(
        telegram_bot_token="token",
        backend_api_url="https://api.example.test/v1",
    )

    assert settings.validate_runtime_configuration() == []
