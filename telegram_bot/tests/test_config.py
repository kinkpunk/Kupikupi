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
        telegram_webapp_url="https://app.example.test",
        support_contact_url="mailto:support@example.test",
        privacy_policy_url="https://app.example.test/privacy",
        terms_url="https://app.example.test/terms",
    )

    assert settings.validate_runtime_configuration() == []


def test_runtime_configuration_accepts_webhook_mode() -> None:
    settings = BotSettings(
        telegram_bot_token="token",
        backend_api_url="https://api.example.test/v1",
        telegram_webapp_url="https://app.example.test",
        bot_run_mode="webhook",
        telegram_webhook_url="https://bot.example.test/telegram/webhook",
        telegram_webhook_secret="secret",
    )

    assert settings.validate_runtime_configuration() == []


def test_runtime_configuration_requires_webhook_values_in_webhook_mode() -> None:
    settings = BotSettings(
        telegram_bot_token="token",
        backend_api_url="https://api.example.test/v1",
        bot_run_mode="webhook",
        telegram_webhook_url="http://bot.example.test/telegram/webhook",
        telegram_webhook_path="telegram/webhook",
    )

    assert settings.validate_runtime_configuration() == [
        "TELEGRAM_WEBHOOK_URL must be an absolute HTTPS URL in webhook mode.",
        "TELEGRAM_WEBHOOK_SECRET must be set in webhook mode.",
        "TELEGRAM_WEBHOOK_PATH must start with '/'.",
    ]


def test_runtime_configuration_rejects_unknown_run_mode() -> None:
    settings = BotSettings(
        telegram_bot_token="token",
        backend_api_url="https://api.example.test/v1",
        bot_run_mode="worker",
    )

    assert settings.validate_runtime_configuration() == ["BOT_RUN_MODE must be polling or webhook."]


def test_runtime_configuration_requires_absolute_webapp_url() -> None:
    settings = BotSettings(
        telegram_bot_token="token",
        backend_api_url="https://api.example.test/v1",
        telegram_webapp_url="/webapp",
    )

    assert settings.validate_runtime_configuration() == [
        "TELEGRAM_WEBAPP_URL must be an absolute http(s) URL."
    ]


def test_runtime_configuration_requires_absolute_public_urls() -> None:
    settings = BotSettings(
        telegram_bot_token="token",
        backend_api_url="https://api.example.test/v1",
        support_contact_url="support",
        privacy_policy_url="/privacy",
        terms_url="/terms",
    )

    assert settings.validate_runtime_configuration() == [
        "SUPPORT_CONTACT_URL must be an absolute http(s) or mailto URL.",
        "PRIVACY_POLICY_URL must be an absolute http(s) or mailto URL.",
        "TERMS_URL must be an absolute http(s) or mailto URL.",
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
