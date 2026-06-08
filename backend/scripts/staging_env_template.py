import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StagingEnvTemplate:
    backend_env: str
    bot_env: str
    webapp_env: str
    operator_env: str


def build_staging_env_template(
    *,
    api_base_url: str,
    webapp_url: str,
    telegram_bot_token: str = "replace-with-staging-bot-token",
    telegram_allowed_user_ids: str = "123456",
    support_contact_url: str = "mailto:support@example.test",
    privacy_policy_url: str = "https://app.staging.kupikupi.example/privacy",
    terms_url: str = "https://app.staging.kupikupi.example/terms",
    jwt_secret_key: str = "replace-with-long-random-secret",
    database_url: str = "postgresql+asyncpg://user:pass@db.example.test:5432/kupikupi",
    redis_url: str = "redis://redis.example.test:6379/0",
    error_reporting_endpoint_url: str = "https://errors.example.test/events",
    observability_dashboard_url: str = "https://dashboards.example.test/kupikupi-staging",
    alert_contact_url: str = "mailto:oncall@example.test",
    operator_admin_access_token: str = "replace-with-staging-admin-token",
    bot_run_mode: str = "polling",
    telegram_webhook_url: str = "",
    telegram_webhook_secret: str = "",
) -> StagingEnvTemplate:
    webapp_origin = _origin(webapp_url)
    error_reporting_enabled = "1" if error_reporting_endpoint_url else "0"
    backend_env = "\n".join(
        [
            'APP_NAME="Kupikupi API"',
            'APP_VERSION="staging"',
            'ENVIRONMENT="staging"',
            'API_V1_PREFIX="/v1"',
            f'DATABASE_URL="{database_url}"',
            f'REDIS_URL="{redis_url}"',
            f'JWT_SECRET_KEY="{jwt_secret_key}"',
            'JWT_ALGORITHM="HS256"',
            'ACCESS_TOKEN_TTL_SECONDS="900"',
            'REFRESH_TOKEN_TTL_SECONDS="2592000"',
            f'TELEGRAM_BOT_TOKEN="{telegram_bot_token}"',
            f'TELEGRAM_ALLOWED_USER_IDS="{telegram_allowed_user_ids}"',
            f'CORS_ALLOWED_ORIGINS="{webapp_origin}"',
            'RUN_MIGRATIONS="1"',
            'RUN_SEED="0"',
            'SOURCE_SYNC_SCHEDULE_SECONDS="300"',
            'NOTIFICATIONS_GENERATE_SCHEDULE_SECONDS="300"',
            'NOTIFICATIONS_DISPATCH_SCHEDULE_SECONDS="120"',
            'ANALYTICS_RECOMPUTE_SCHEDULE_SECONDS="3600"',
            'FX_RATE_UPDATE_SCHEDULE_SECONDS="43200"',
            'RETENTION_CLEANUP_SCHEDULE_SECONDS="86400"',
            'NOTIFICATION_RETENTION_DAYS="180"',
            'SOURCE_SYNC_RETENTION_DAYS="90"',
            'FX_RATE_SOURCE_URL="https://api.exchangerate.host/latest?base=EUR&symbols=CZK"',
            'FX_RATE_CURRENCIES="CZK"',
            f'ERROR_REPORTING_ENABLED="{error_reporting_enabled}"',
            f'ERROR_REPORTING_ENDPOINT_URL="{error_reporting_endpoint_url}"',
            f'OBSERVABILITY_DASHBOARD_URL="{observability_dashboard_url}"',
            f'ALERT_CONTACT_URL="{alert_contact_url}"',
        ]
    )
    bot_env = "\n".join(
        [
            f'TELEGRAM_BOT_TOKEN="{telegram_bot_token}"',
            f'BACKEND_API_URL="{api_base_url}"',
            'BACKEND_ACCESS_TOKEN=""',
            f'TELEGRAM_WEBAPP_URL="{webapp_url}"',
            f'TELEGRAM_ALLOWED_USER_IDS="{telegram_allowed_user_ids}"',
            f'SUPPORT_CONTACT_URL="{support_contact_url}"',
            f'PRIVACY_POLICY_URL="{privacy_policy_url}"',
            f'TERMS_URL="{terms_url}"',
            f'BOT_RUN_MODE="{bot_run_mode}"',
            'BOT_POLLING_TIMEOUT_SECONDS="30"',
            f'TELEGRAM_WEBHOOK_URL="{telegram_webhook_url}"',
            f'TELEGRAM_WEBHOOK_SECRET="{telegram_webhook_secret}"',
            'TELEGRAM_WEBHOOK_PATH="/telegram/webhook"',
            'WEBHOOK_HOST="0.0.0.0"',
            'WEBHOOK_PORT="8080"',
        ]
    )
    webapp_env = "\n".join(
        [
            'NEXT_PUBLIC_APP_ENV="staging"',
            f'NEXT_PUBLIC_API_BASE_URL="{api_base_url}"',
            'NEXT_PUBLIC_DEMO_ACCESS_TOKEN=""',
            f'NEXT_PUBLIC_SUPPORT_CONTACT_URL="{support_contact_url}"',
            f'NEXT_PUBLIC_PRIVACY_POLICY_URL="{privacy_policy_url}"',
            f'NEXT_PUBLIC_TERMS_URL="{terms_url}"',
        ]
    )
    operator_env = "\n".join(
        [
            f'KUPIKUPI_API_BASE_URL="{api_base_url}"',
            f'KUPIKUPI_WEBAPP_URL="{webapp_url}"',
            f'KUPIKUPI_SUPPORT_URL="{support_contact_url}"',
            f'KUPIKUPI_PRIVACY_URL="{privacy_policy_url}"',
            f'KUPIKUPI_TERMS_URL="{terms_url}"',
            'KUPIKUPI_ACCESS_TOKEN=""',
            f'KUPIKUPI_ADMIN_ACCESS_TOKEN="{operator_admin_access_token}"',
            'KUPIKUPI_CONFIRM_WATCHLIST="0"',
        ]
    )
    return StagingEnvTemplate(
        backend_env=backend_env + "\n",
        bot_env=bot_env + "\n",
        webapp_env=webapp_env + "\n",
        operator_env=operator_env + "\n",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write Kupikupi staging env templates.")
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--webapp-url", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--telegram-bot-token", default="replace-with-staging-bot-token")
    parser.add_argument("--telegram-allowed-user-ids", default="123456")
    parser.add_argument("--support-contact-url", default="mailto:support@example.test")
    parser.add_argument(
        "--privacy-policy-url",
        default="https://app.staging.kupikupi.example/privacy",
    )
    parser.add_argument("--terms-url", default="https://app.staging.kupikupi.example/terms")
    parser.add_argument("--jwt-secret-key", default="replace-with-long-random-secret")
    parser.add_argument(
        "--database-url",
        default="postgresql+asyncpg://user:pass@db.example.test:5432/kupikupi",
    )
    parser.add_argument("--redis-url", default="redis://redis.example.test:6379/0")
    parser.add_argument(
        "--error-reporting-endpoint-url",
        default="https://errors.example.test/events",
    )
    parser.add_argument(
        "--observability-dashboard-url",
        default="https://dashboards.example.test/kupikupi-staging",
    )
    parser.add_argument("--alert-contact-url", default="mailto:oncall@example.test")
    parser.add_argument(
        "--operator-admin-access-token",
        default="replace-with-staging-admin-token",
    )
    parser.add_argument("--bot-run-mode", default="polling", choices=["polling", "webhook"])
    parser.add_argument("--telegram-webhook-url", default="")
    parser.add_argument("--telegram-webhook-secret", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    template = build_staging_env_template(
        api_base_url=args.api_base_url,
        webapp_url=args.webapp_url,
        telegram_bot_token=args.telegram_bot_token,
        telegram_allowed_user_ids=args.telegram_allowed_user_ids,
        support_contact_url=args.support_contact_url,
        privacy_policy_url=args.privacy_policy_url,
        terms_url=args.terms_url,
        jwt_secret_key=args.jwt_secret_key,
        database_url=args.database_url,
        redis_url=args.redis_url,
        error_reporting_endpoint_url=args.error_reporting_endpoint_url,
        observability_dashboard_url=args.observability_dashboard_url,
        alert_contact_url=args.alert_contact_url,
        operator_admin_access_token=args.operator_admin_access_token,
        bot_run_mode=args.bot_run_mode,
        telegram_webhook_url=args.telegram_webhook_url,
        telegram_webhook_secret=args.telegram_webhook_secret,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "kupikupi-backend.env").write_text(template.backend_env, encoding="utf-8")
    (args.output_dir / "kupikupi-bot.env").write_text(template.bot_env, encoding="utf-8")
    (args.output_dir / "kupikupi-webapp.env").write_text(template.webapp_env, encoding="utf-8")
    (args.output_dir / "kupikupi-operator.env").write_text(
        template.operator_env,
        encoding="utf-8",
    )
    print(f"Wrote staging env templates to {args.output_dir}")


def _origin(value: str) -> str:
    parts = value.split("/", 3)
    return "/".join(parts[:3])


if __name__ == "__main__":
    main()
