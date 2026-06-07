from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def is_production_like(self) -> bool:
        return self.environment.lower() in {"production", "prod", "staging"}

    def validate_runtime_configuration(self) -> list[str]:
        issues = []
        if self.is_production_like and self.jwt_secret_key == "change-me-in-production":
            issues.append("JWT_SECRET_KEY must be changed for production-like environments.")
        return issues

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
