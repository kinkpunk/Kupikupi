import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


@dataclass(frozen=True)
class PreflightReport:
    issues: list[str]

    @property
    def passed(self) -> bool:
        return not self.issues


def run_preflight(
    *,
    backend_env: dict[str, str],
    bot_env: dict[str, str],
    webapp_env: dict[str, str],
    operator_env: dict[str, str] | None = None,
) -> PreflightReport:
    issues = []
    issues.extend(_validate_backend_env(backend_env))
    issues.extend(_validate_bot_env(bot_env))
    issues.extend(_validate_webapp_env(webapp_env))
    if operator_env is not None:
        issues.extend(_validate_operator_env(operator_env))
    issues.extend(_validate_cross_service_env(backend_env, bot_env, webapp_env))
    if operator_env is not None:
        issues.extend(_validate_operator_cross_service_env(operator_env, bot_env, webapp_env))
    return PreflightReport(issues=issues)


def load_env_file(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def merged_env(path: Path | None) -> dict[str, str]:
    values = dict(os.environ)
    values.update(load_env_file(path))
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Kupikupi staging environment values.")
    parser.add_argument("--backend-env", type=Path, help="Backend env file.")
    parser.add_argument("--bot-env", type=Path, help="Telegram Bot env file.")
    parser.add_argument("--webapp-env", type=Path, help="WebApp build/runtime env file.")
    parser.add_argument("--operator-env", type=Path, help="Operator env file for smoke scripts.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_preflight(
        backend_env=merged_env(args.backend_env),
        bot_env=merged_env(args.bot_env),
        webapp_env=merged_env(args.webapp_env),
        operator_env=merged_env(args.operator_env) if args.operator_env else None,
    )

    if report.passed:
        print("Kupikupi staging preflight passed.")
        raise SystemExit(0)

    print("Kupikupi staging preflight failed:")
    for issue in report.issues:
        print(f"- {issue}")
    raise SystemExit(1)


def _validate_backend_env(env: dict[str, str]) -> list[str]:
    issues = []
    if env.get("ENVIRONMENT") != "staging":
        issues.append("backend ENVIRONMENT must be staging.")
    if env.get("JWT_SECRET_KEY") in {None, "", "change-me-in-production"}:
        issues.append("backend JWT_SECRET_KEY must be set and not use the default.")
    if not env.get("TELEGRAM_BOT_TOKEN"):
        issues.append("backend TELEGRAM_BOT_TOKEN must be set.")
    if _has_local_hostname(env.get("DATABASE_URL", "")):
        issues.append("backend DATABASE_URL must not point to localhost.")
    if _has_local_hostname(env.get("REDIS_URL", "")):
        issues.append("backend REDIS_URL must not point to localhost.")
    if _contains_local_origin(env.get("CORS_ALLOWED_ORIGINS", "")):
        issues.append("backend CORS_ALLOWED_ORIGINS must not contain localhost or '*'.")
    if not _valid_allowlist(env.get("TELEGRAM_ALLOWED_USER_IDS", "")):
        issues.append("backend TELEGRAM_ALLOWED_USER_IDS must be comma-separated numeric IDs.")
    if env.get("ERROR_REPORTING_ENABLED") not in {"1", "true", "True"}:
        issues.append("backend ERROR_REPORTING_ENABLED must be enabled for staging.")
    if not _is_http_url(env.get("ERROR_REPORTING_ENDPOINT_URL", "")):
        issues.append("backend ERROR_REPORTING_ENDPOINT_URL must be absolute http(s).")
    if not _is_http_url(env.get("OBSERVABILITY_DASHBOARD_URL", "")):
        issues.append("backend OBSERVABILITY_DASHBOARD_URL must be an absolute http(s) URL.")
    if not _is_public_url(env.get("ALERT_CONTACT_URL", "")):
        issues.append("backend ALERT_CONTACT_URL must be an absolute http(s) or mailto URL.")
    return issues


def _validate_bot_env(env: dict[str, str]) -> list[str]:
    issues = []
    run_mode = env.get("BOT_RUN_MODE", "polling")
    if not env.get("TELEGRAM_BOT_TOKEN"):
        issues.append("bot TELEGRAM_BOT_TOKEN must be set.")
    if run_mode not in {"polling", "webhook"}:
        issues.append("bot BOT_RUN_MODE must be polling or webhook.")
    if not _is_http_url(env.get("BACKEND_API_URL", "")):
        issues.append("bot BACKEND_API_URL must be an absolute http(s) URL.")
    if not _is_https_url(env.get("TELEGRAM_WEBAPP_URL", "")):
        issues.append("bot TELEGRAM_WEBAPP_URL must be an absolute HTTPS URL.")
    if not _valid_allowlist(env.get("TELEGRAM_ALLOWED_USER_IDS", "")):
        issues.append("bot TELEGRAM_ALLOWED_USER_IDS must be comma-separated numeric IDs.")
    if not _is_public_url(env.get("SUPPORT_CONTACT_URL", "")):
        issues.append("bot SUPPORT_CONTACT_URL must be an absolute http(s) or mailto URL.")
    if not _is_public_url(env.get("PRIVACY_POLICY_URL", "")):
        issues.append("bot PRIVACY_POLICY_URL must be an absolute http(s) or mailto URL.")
    if not _is_public_url(env.get("TERMS_URL", "")):
        issues.append("bot TERMS_URL must be an absolute http(s) or mailto URL.")
    if run_mode == "webhook":
        if not _is_https_url(env.get("TELEGRAM_WEBHOOK_URL", "")):
            issues.append("bot TELEGRAM_WEBHOOK_URL must be an absolute HTTPS URL in webhook mode.")
        if not env.get("TELEGRAM_WEBHOOK_SECRET"):
            issues.append("bot TELEGRAM_WEBHOOK_SECRET must be set in webhook mode.")
        if not env.get("TELEGRAM_WEBHOOK_PATH", "/").startswith("/"):
            issues.append("bot TELEGRAM_WEBHOOK_PATH must start with '/'.")
    return issues


def _validate_webapp_env(env: dict[str, str]) -> list[str]:
    issues = []
    if env.get("NEXT_PUBLIC_APP_ENV") != "staging":
        issues.append("webapp NEXT_PUBLIC_APP_ENV must be staging.")
    if not _is_https_url(env.get("NEXT_PUBLIC_API_BASE_URL", "")):
        issues.append("webapp NEXT_PUBLIC_API_BASE_URL must be an absolute HTTPS URL.")
    if env.get("NEXT_PUBLIC_DEMO_ACCESS_TOKEN"):
        issues.append("webapp NEXT_PUBLIC_DEMO_ACCESS_TOKEN must be empty in staging.")
    if not _is_public_url(env.get("NEXT_PUBLIC_SUPPORT_CONTACT_URL", "")):
        issues.append("webapp NEXT_PUBLIC_SUPPORT_CONTACT_URL must be absolute http(s) or mailto.")
    if not _is_public_url(env.get("NEXT_PUBLIC_PRIVACY_POLICY_URL", "")):
        issues.append("webapp NEXT_PUBLIC_PRIVACY_POLICY_URL must be absolute http(s) or mailto.")
    if not _is_public_url(env.get("NEXT_PUBLIC_TERMS_URL", "")):
        issues.append("webapp NEXT_PUBLIC_TERMS_URL must be absolute http(s) or mailto.")
    return issues


def _validate_operator_env(env: dict[str, str]) -> list[str]:
    issues = []
    if not _is_https_url(env.get("KUPIKUPI_API_BASE_URL", "")):
        issues.append("operator KUPIKUPI_API_BASE_URL must be an absolute HTTPS URL.")
    if not _is_https_url(env.get("KUPIKUPI_WEBAPP_URL", "")):
        issues.append("operator KUPIKUPI_WEBAPP_URL must be an absolute HTTPS URL.")
    if not _is_public_url(env.get("KUPIKUPI_SUPPORT_URL", "")):
        issues.append("operator KUPIKUPI_SUPPORT_URL must be absolute http(s) or mailto.")
    if not _is_public_url(env.get("KUPIKUPI_PRIVACY_URL", "")):
        issues.append("operator KUPIKUPI_PRIVACY_URL must be absolute http(s) or mailto.")
    if not _is_public_url(env.get("KUPIKUPI_TERMS_URL", "")):
        issues.append("operator KUPIKUPI_TERMS_URL must be absolute http(s) or mailto.")
    admin_token = env.get("KUPIKUPI_ADMIN_ACCESS_TOKEN", "")
    if not admin_token or admin_token == "replace-with-staging-admin-token":
        issues.append("operator KUPIKUPI_ADMIN_ACCESS_TOKEN must be set.")
    confirm_watchlist = env.get("KUPIKUPI_CONFIRM_WATCHLIST", "0")
    if confirm_watchlist not in {"0", "1"}:
        issues.append("operator KUPIKUPI_CONFIRM_WATCHLIST must be 0 or 1.")
    run_notification_smoke = env.get("KUPIKUPI_RUN_NOTIFICATION_SMOKE", "0")
    if run_notification_smoke not in {"0", "1"}:
        issues.append("operator KUPIKUPI_RUN_NOTIFICATION_SMOKE must be 0 or 1.")
    dispatch_limit = env.get("KUPIKUPI_NOTIFICATION_DISPATCH_LIMIT", "100")
    if not dispatch_limit.isdecimal() or int(dispatch_limit) < 1:
        issues.append("operator KUPIKUPI_NOTIFICATION_DISPATCH_LIMIT must be a positive integer.")
    demo_data_only = env.get("KUPIKUPI_DEMO_DATA_ONLY", "0")
    if demo_data_only not in {"0", "1"}:
        issues.append("operator KUPIKUPI_DEMO_DATA_ONLY must be 0 or 1.")
    if demo_data_only != "1" and not env.get("KUPIKUPI_STORE_FEED_CONFIG", ""):
        issues.append("operator KUPIKUPI_STORE_FEED_CONFIG must be set unless demo-data-only.")
    return issues


def _validate_cross_service_env(
    backend_env: dict[str, str],
    bot_env: dict[str, str],
    webapp_env: dict[str, str],
) -> list[str]:
    issues = []
    if backend_env.get("TELEGRAM_BOT_TOKEN") != bot_env.get("TELEGRAM_BOT_TOKEN"):
        issues.append("backend and bot TELEGRAM_BOT_TOKEN values must match.")
    if backend_env.get("TELEGRAM_ALLOWED_USER_IDS", "") != bot_env.get(
        "TELEGRAM_ALLOWED_USER_IDS", ""
    ):
        issues.append("backend and bot TELEGRAM_ALLOWED_USER_IDS values must match.")
    if bot_env.get("BACKEND_API_URL") != webapp_env.get("NEXT_PUBLIC_API_BASE_URL"):
        issues.append("bot BACKEND_API_URL must match webapp NEXT_PUBLIC_API_BASE_URL.")
    webapp_origin = _origin(bot_env.get("TELEGRAM_WEBAPP_URL", ""))
    backend_cors_origins = _split_csv(backend_env.get("CORS_ALLOWED_ORIGINS", ""))
    if webapp_origin and webapp_origin not in backend_cors_origins:
        issues.append("backend CORS_ALLOWED_ORIGINS must include the Telegram WebApp origin.")
    return issues


def _validate_operator_cross_service_env(
    operator_env: dict[str, str],
    bot_env: dict[str, str],
    webapp_env: dict[str, str],
) -> list[str]:
    issues = []
    if operator_env.get("KUPIKUPI_API_BASE_URL") != webapp_env.get("NEXT_PUBLIC_API_BASE_URL"):
        issues.append(
            "operator KUPIKUPI_API_BASE_URL must match webapp NEXT_PUBLIC_API_BASE_URL."
        )
    if operator_env.get("KUPIKUPI_WEBAPP_URL") != bot_env.get("TELEGRAM_WEBAPP_URL"):
        issues.append("operator KUPIKUPI_WEBAPP_URL must match bot TELEGRAM_WEBAPP_URL.")
    if operator_env.get("KUPIKUPI_PRIVACY_URL") != webapp_env.get(
        "NEXT_PUBLIC_PRIVACY_POLICY_URL"
    ):
        issues.append(
            "operator KUPIKUPI_PRIVACY_URL must match webapp NEXT_PUBLIC_PRIVACY_POLICY_URL."
        )
    if operator_env.get("KUPIKUPI_TERMS_URL") != webapp_env.get("NEXT_PUBLIC_TERMS_URL"):
        issues.append("operator KUPIKUPI_TERMS_URL must match webapp NEXT_PUBLIC_TERMS_URL.")
    return issues


def _has_local_hostname(value: str) -> bool:
    return urlparse(value).hostname in LOCAL_HOSTNAMES


def _contains_local_origin(value: str) -> bool:
    origins = _split_csv(value)
    return "*" in origins or any(_has_local_hostname(origin) for origin in origins)


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _is_public_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return bool(parsed.netloc)
    if parsed.scheme == "mailto":
        return bool(parsed.path)
    return False


def _valid_allowlist(value: str) -> bool:
    return all(item.strip().isdecimal() for item in value.split(",") if item.strip())


def _origin(value: str) -> str:
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


if __name__ == "__main__":
    main()
