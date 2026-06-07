from app.core.config import Settings


def test_runtime_configuration_allows_local_default_secret() -> None:
    settings = Settings(environment="local", jwt_secret_key="change-me-in-production")

    assert settings.validate_runtime_configuration() == []


def test_runtime_configuration_rejects_default_secret_in_production() -> None:
    settings = Settings(
        environment="production",
        jwt_secret_key="change-me-in-production",
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
        database_url="postgresql+asyncpg://user:pass@db.example.test:5432/kupikupi",
        redis_url="redis://redis.example.test:6379/0",
        cors_allowed_origins="https://app.example.test",
    )

    assert settings.validate_runtime_configuration() == []


def test_runtime_configuration_rejects_local_dependencies_in_production() -> None:
    settings = Settings(
        environment="staging",
        jwt_secret_key="custom-secret",
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
