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
        support_contact_url="mailto:support@example.test",
        privacy_policy_url="https://app.example.test/privacy",
    )

    assert settings.validate_runtime_configuration() == []


def test_runtime_configuration_requires_absolute_public_urls() -> None:
    settings = BotSettings(
        telegram_bot_token="token",
        backend_api_url="https://api.example.test/v1",
        support_contact_url="support",
        privacy_policy_url="/privacy",
    )

    assert settings.validate_runtime_configuration() == [
        "SUPPORT_CONTACT_URL must be an absolute http(s) or mailto URL.",
        "PRIVACY_POLICY_URL must be an absolute http(s) or mailto URL.",
    ]


def test_allowed_user_ids_parses_comma_separated_ids() -> None:
    settings = BotSettings(
        telegram_bot_token="token",
        telegram_allowed_user_ids="123, 456,789",
    )

    assert settings.allowed_user_ids == {123, 456, 789}
    assert settings.validate_runtime_configuration() == []


def test_runtime_configuration_rejects_invalid_allowed_user_ids() -> None:
    settings = BotSettings(
        telegram_bot_token="token",
        telegram_allowed_user_ids="123,not-a-number",
    )

    assert settings.validate_runtime_configuration() == [
        "TELEGRAM_ALLOWED_USER_IDS must be a comma-separated list of integers."
    ]
