from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    telegram_bot_token: str = ""
    backend_api_url: str = "http://localhost:8000/v1"
    backend_access_token: str | None = None
    telegram_webapp_url: str | None = None
    telegram_allowed_user_ids: str = ""
    support_contact_url: str | None = None
    privacy_policy_url: str | None = None
    bot_run_mode: str = "polling"
    bot_polling_timeout_seconds: int = Field(default=30, ge=1)
    telegram_webhook_url: str | None = None
    telegram_webhook_secret: str | None = None
    telegram_webhook_path: str = "/telegram/webhook"
    webhook_host: str = "0.0.0.0"
    webhook_port: int = Field(default=8080, ge=1, le=65535)

    @property
    def allowed_user_ids(self) -> set[int]:
        values = set()
        for item in self.telegram_allowed_user_ids.split(","):
            item = item.strip()
            if item:
                values.add(int(item))
        return values

    def validate_runtime_configuration(self) -> list[str]:
        issues = []
        run_mode = self.bot_run_mode.casefold()
        if not self.telegram_bot_token.strip():
            issues.append("TELEGRAM_BOT_TOKEN is required.")
        if run_mode not in {"polling", "webhook"}:
            issues.append("BOT_RUN_MODE must be polling or webhook.")
        parsed_backend_url = urlparse(self.backend_api_url)
        if parsed_backend_url.scheme not in {"http", "https"} or not parsed_backend_url.netloc:
            issues.append("BACKEND_API_URL must be an absolute http(s) URL.")
        if self.telegram_webapp_url and not _is_allowed_http_url(self.telegram_webapp_url):
            issues.append("TELEGRAM_WEBAPP_URL must be an absolute http(s) URL.")
        if self.support_contact_url and not _is_allowed_public_url(self.support_contact_url):
            issues.append("SUPPORT_CONTACT_URL must be an absolute http(s) or mailto URL.")
        if self.privacy_policy_url and not _is_allowed_public_url(self.privacy_policy_url):
            issues.append("PRIVACY_POLICY_URL must be an absolute http(s) or mailto URL.")
        if run_mode == "webhook":
            if not self.telegram_webhook_url or not _is_https_url(self.telegram_webhook_url):
                issues.append("TELEGRAM_WEBHOOK_URL must be an absolute HTTPS URL in webhook mode.")
            if not self.telegram_webhook_secret:
                issues.append("TELEGRAM_WEBHOOK_SECRET must be set in webhook mode.")
            if not self.telegram_webhook_path.startswith("/"):
                issues.append("TELEGRAM_WEBHOOK_PATH must start with '/'.")
        try:
            _ = self.allowed_user_ids
        except ValueError:
            issues.append("TELEGRAM_ALLOWED_USER_IDS must be a comma-separated list of integers.")
        return issues

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> BotSettings:
    return BotSettings()


def _is_allowed_public_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return _is_allowed_http_url(value)
    if parsed.scheme == "mailto":
        return bool(parsed.path)
    return False


def _is_allowed_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)
