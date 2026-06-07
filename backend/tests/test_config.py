from app.core.config import Settings


def test_runtime_configuration_allows_local_default_secret() -> None:
    settings = Settings(environment="local", jwt_secret_key="change-me-in-production")

    assert settings.validate_runtime_configuration() == []


def test_runtime_configuration_rejects_default_secret_in_production() -> None:
    settings = Settings(environment="production", jwt_secret_key="change-me-in-production")

    assert settings.validate_runtime_configuration() == [
        "JWT_SECRET_KEY must be changed for production-like environments."
    ]


def test_runtime_configuration_allows_custom_secret_in_production() -> None:
    settings = Settings(environment="production", jwt_secret_key="custom-secret")

    assert settings.validate_runtime_configuration() == []
