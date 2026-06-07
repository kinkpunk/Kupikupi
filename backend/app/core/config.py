from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


class Settings(BaseSettings):
    app_name: str = "Kupikupi API"
    app_version: str = "0.1.0"
    environment: str = "local"
    api_v1_prefix: str = "/v1"

    database_url: str = Field(
        default="postgresql+asyncpg://kupikupi:kupikupi@localhost:5432/kupikupi"
    )
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 2_592_000

    telegram_bot_token: str | None = None
    cors_allowed_origins: str = "http://localhost:3000"

    source_sync_schedule_seconds: int = 300
    notifications_generate_schedule_seconds: int = 300
    notifications_dispatch_schedule_seconds: int = 120
    analytics_recompute_schedule_seconds: int = 3600
    fx_rate_update_schedule_seconds: int = 43_200
    fx_rate_source_url: str = "https://api.exchangerate.host/latest?base=EUR&symbols=CZK"
    fx_rate_currencies: str = "CZK"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def fx_currencies(self) -> list[str]:
        return [
            currency.strip().upper()
            for currency in self.fx_rate_currencies.split(",")
            if currency.strip()
        ]

    @property
    def is_production_like(self) -> bool:
        return self.environment.lower() in {"production", "prod", "staging"}

    def validate_runtime_configuration(self) -> list[str]:
        issues = []
        if not self.is_production_like:
            return issues

        if self.jwt_secret_key == "change-me-in-production":
            issues.append("JWT_SECRET_KEY must be changed for production-like environments.")
        if _has_local_hostname(self.database_url):
            issues.append(
                "DATABASE_URL must not point to localhost in production-like environments."
            )
        if _has_local_hostname(self.redis_url):
            issues.append("REDIS_URL must not point to localhost in production-like environments.")
        if "*" in self.cors_origins:
            issues.append(
                "CORS_ALLOWED_ORIGINS must not contain '*' in production-like environments."
            )
        if any(_has_local_hostname(origin) for origin in self.cors_origins):
            issues.append(
                "CORS_ALLOWED_ORIGINS must not contain localhost origins "
                "in production-like environments."
            )
        return issues

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


def _has_local_hostname(value: str) -> bool:
    hostname = urlparse(value).hostname
    return hostname in LOCAL_HOSTNAMES


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
