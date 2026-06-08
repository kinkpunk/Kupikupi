from app.core.config import Settings


def test_runtime_configuration_allows_local_default_secret() -> None:
    settings = Settings(environment="local", jwt_secret_key="change-me-in-production")

    assert settings.validate_runtime_configuration() == []


def test_runtime_configuration_rejects_default_secret_in_production() -> None:
    settings = Settings(
        environment="production",
        jwt_secret_key="change-me-in-production",
        telegram_bot_token="bot-token",
        database_url="postgresql+asyncpg://user:pass@db.example.test:5432/kupikupi",
        redis_url="redis://redis.example.test:6379/0",
        cors_allowed_origins="https://app.example.test",
    )

    assert settings.validate_runtime_configuration() == [
        "JWT_SECRET_KEY must be changed for production-like environments."
    ]


def test_runtime_configuration_allows_custom_secret_in_production() -> None:
    settings = Settings(
        environment="production",
        jwt_secret_key="custom-secret",
        telegram_bot_token="bot-token",
        database_url="postgresql+asyncpg://user:pass@db.example.test:5432/kupikupi",
        redis_url="redis://redis.example.test:6379/0",
        cors_allowed_origins="https://app.example.test",
    )

    assert settings.validate_runtime_configuration() == []


def test_runtime_configuration_rejects_local_dependencies_in_production() -> None:
    settings = Settings(
        environment="staging",
        jwt_secret_key="custom-secret",
        telegram_bot_token="bot-token",
        database_url="postgresql+asyncpg://kupikupi:kupikupi@localhost:5432/kupikupi",
        redis_url="redis://127.0.0.1:6379/0",
        cors_allowed_origins="https://app.example.test,http://localhost:3000,*",
    )

    assert settings.validate_runtime_configuration() == [
        "DATABASE_URL must not point to localhost in production-like environments.",
        "REDIS_URL must not point to localhost in production-like environments.",
        "CORS_ALLOWED_ORIGINS must not contain '*' in production-like environments.",
        "CORS_ALLOWED_ORIGINS must not contain localhost origins in production-like environments.",
    ]


def test_runtime_configuration_requires_telegram_bot_token_in_production() -> None:
    settings = Settings(
        environment="staging",
        jwt_secret_key="custom-secret",
        telegram_bot_token=None,
        database_url="postgresql+asyncpg://user:pass@db.example.test:5432/kupikupi",
        redis_url="redis://redis.example.test:6379/0",
        cors_allowed_origins="https://app.example.test",
    )

    assert settings.validate_runtime_configuration() == [
        "TELEGRAM_BOT_TOKEN must be configured for production-like environments."
    ]


def test_allowed_telegram_user_ids_parses_comma_separated_ids() -> None:
    settings = Settings(telegram_allowed_user_ids="123, 456,789")

    assert settings.allowed_telegram_user_ids == {123, 456, 789}
    assert settings.is_telegram_user_allowed(456) is True
    assert settings.is_telegram_user_allowed(999) is False


def test_runtime_configuration_rejects_invalid_telegram_allowlist() -> None:
    settings = Settings(
        environment="staging",
        jwt_secret_key="custom-secret",
        telegram_bot_token="bot-token",
        database_url="postgresql+asyncpg://user:pass@db.example.test:5432/kupikupi",
        redis_url="redis://redis.example.test:6379/0",
        cors_allowed_origins="https://app.example.test",
        telegram_allowed_user_ids="123,not-a-number",
    )

    assert settings.validate_runtime_configuration() == [
        "TELEGRAM_ALLOWED_USER_IDS must be a comma-separated list of integers."
    ]
