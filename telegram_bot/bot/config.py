from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    telegram_bot_token: str = ""
    backend_api_url: str = "http://localhost:8000/v1"
    backend_access_token: str | None = None
    telegram_webapp_url: str | None = None
    support_contact_url: str | None = None
    privacy_policy_url: str | None = None
    bot_polling_timeout_seconds: int = Field(default=30, ge=1)

    def validate_runtime_configuration(self) -> list[str]:
        issues = []
        if not self.telegram_bot_token.strip():
            issues.append("TELEGRAM_BOT_TOKEN is required.")
        parsed_backend_url = urlparse(self.backend_api_url)
        if parsed_backend_url.scheme not in {"http", "https"} or not parsed_backend_url.netloc:
            issues.append("BACKEND_API_URL must be an absolute http(s) URL.")
        if self.support_contact_url and not _is_allowed_public_url(self.support_contact_url):
            issues.append("SUPPORT_CONTACT_URL must be an absolute http(s) or mailto URL.")
        if self.privacy_policy_url and not _is_allowed_public_url(self.privacy_policy_url):
            issues.append("PRIVACY_POLICY_URL must be an absolute http(s) or mailto URL.")
        return issues

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> BotSettings:
    return BotSettings()


def _is_allowed_public_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return bool(parsed.netloc)
    if parsed.scheme == "mailto":
        return bool(parsed.path)
    return False
