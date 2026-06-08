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
    telegram_allowed_user_ids: str = ""
    cors_allowed_origins: str = "http://localhost:3000"

    source_sync_schedule_seconds: int = 300
    notifications_generate_schedule_seconds: int = 300
    notifications_dispatch_schedule_seconds: int = 120
    analytics_recompute_schedule_seconds: int = 3600
    fx_rate_update_schedule_seconds: int = 43_200
    retention_cleanup_schedule_seconds: int = 86_400
    notification_retention_days: int = 180
    source_sync_retention_days: int = 90
    fx_rate_source_url: str = "https://api.exchangerate.host/latest?base=EUR&symbols=CZK"
    fx_rate_currencies: str = "CZK"
    error_reporting_enabled: bool = False
    error_reporting_endpoint_url: str | None = None

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
    def allowed_telegram_user_ids(self) -> set[int]:
        values = set()
        for item in self.telegram_allowed_user_ids.split(","):
            item = item.strip()
            if item:
                values.add(int(item))
        return values

    def is_telegram_user_allowed(self, telegram_id: int) -> bool:
        allowed_user_ids = self.allowed_telegram_user_ids
        return not allowed_user_ids or telegram_id in allowed_user_ids

    @property
    def is_production_like(self) -> bool:
        return self.environment.lower() in {"production", "prod", "staging"}

    def validate_runtime_configuration(self) -> list[str]:
        issues = []
        if not self.is_production_like:
            return issues

        if self.jwt_secret_key == "change-me-in-production":
            issues.append("JWT_SECRET_KEY must be changed for production-like environments.")
        if not self.telegram_bot_token:
            issues.append("TELEGRAM_BOT_TOKEN must be configured for production-like environments.")
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
        try:
            _ = self.allowed_telegram_user_ids
        except ValueError:
            issues.append("TELEGRAM_ALLOWED_USER_IDS must be a comma-separated list of integers.")
        return issues

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


def _has_local_hostname(value: str) -> bool:
    hostname = urlparse(value).hostname
    return hostname in LOCAL_HOSTNAMES


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
