from scripts.staging_preflight import run_preflight


def test_staging_preflight_accepts_valid_environment() -> None:
    envs = _valid_envs()

    report = run_preflight(**envs)

    assert report.passed is True
    assert report.issues == []


def test_staging_preflight_rejects_missing_and_mismatched_values() -> None:
    envs = _valid_envs()
    envs["backend_env"]["TELEGRAM_BOT_TOKEN"] = ""
    envs["backend_env"]["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
    envs["backend_env"]["CORS_ALLOWED_ORIGINS"] = "http://localhost:3000"
    envs["backend_env"]["ERROR_REPORTING_ENABLED"] = "0"
    envs["backend_env"]["OBSERVABILITY_DASHBOARD_URL"] = ""
    envs["backend_env"]["ALERT_CONTACT_URL"] = "not-a-url"
    envs["bot_env"]["BACKEND_API_URL"] = "https://other.example.test/v1"
    envs["webapp_env"]["NEXT_PUBLIC_DEMO_ACCESS_TOKEN"] = "demo-token"

    report = run_preflight(**envs)

    assert report.passed is False
    assert "backend TELEGRAM_BOT_TOKEN must be set." in report.issues
    assert "backend DATABASE_URL must not point to localhost." in report.issues
    assert "backend CORS_ALLOWED_ORIGINS must not contain localhost or '*'." in report.issues
    assert "backend ERROR_REPORTING_ENABLED must be enabled for staging." in report.issues
    assert (
        "backend OBSERVABILITY_DASHBOARD_URL must be an absolute http(s) URL."
        in report.issues
    )
    assert "backend ALERT_CONTACT_URL must be an absolute http(s) or mailto URL." in report.issues
    assert "backend and bot TELEGRAM_BOT_TOKEN values must match." in report.issues
    assert "bot BACKEND_API_URL must match webapp NEXT_PUBLIC_API_BASE_URL." in report.issues
    assert "webapp NEXT_PUBLIC_DEMO_ACCESS_TOKEN must be empty in staging." in report.issues


def test_staging_preflight_rejects_invalid_allowlist() -> None:
    envs = _valid_envs()
    envs["backend_env"]["TELEGRAM_ALLOWED_USER_IDS"] = "123,abc"

    report = run_preflight(**envs)

    assert report.passed is False
    assert "backend TELEGRAM_ALLOWED_USER_IDS must be comma-separated numeric IDs." in report.issues
    assert "backend and bot TELEGRAM_ALLOWED_USER_IDS values must match." in report.issues


def _valid_envs() -> dict[str, dict[str, str]]:
    api_url = "https://api.staging.kupikupi.example/v1"
    webapp_url = "https://app.staging.kupikupi.example"
    allowlist = "123,456"
    bot_token = "staging-bot-token"
    return {
        "backend_env": {
            "ENVIRONMENT": "staging",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@db.example.test:5432/kupikupi",
            "REDIS_URL": "redis://redis.example.test:6379/0",
            "JWT_SECRET_KEY": "custom-secret",
            "TELEGRAM_BOT_TOKEN": bot_token,
            "TELEGRAM_ALLOWED_USER_IDS": allowlist,
            "CORS_ALLOWED_ORIGINS": "https://app.staging.kupikupi.example",
            "ERROR_REPORTING_ENABLED": "1",
            "ERROR_REPORTING_ENDPOINT_URL": "https://errors.example.test/events",
            "OBSERVABILITY_DASHBOARD_URL": "https://dashboards.example.test/kupikupi-staging",
            "ALERT_CONTACT_URL": "mailto:oncall@example.test",
        },
        "bot_env": {
            "TELEGRAM_BOT_TOKEN": bot_token,
            "BACKEND_API_URL": api_url,
            "BACKEND_ACCESS_TOKEN": "",
            "TELEGRAM_WEBAPP_URL": webapp_url,
            "TELEGRAM_ALLOWED_USER_IDS": allowlist,
            "SUPPORT_CONTACT_URL": "mailto:support@example.test",
            "PRIVACY_POLICY_URL": "https://app.staging.kupikupi.example/privacy",
        },
        "webapp_env": {
            "NEXT_PUBLIC_APP_ENV": "staging",
            "NEXT_PUBLIC_API_BASE_URL": api_url,
            "NEXT_PUBLIC_DEMO_ACCESS_TOKEN": "",
            "NEXT_PUBLIC_SUPPORT_CONTACT_URL": "mailto:support@example.test",
            "NEXT_PUBLIC_PRIVACY_POLICY_URL": "https://app.staging.kupikupi.example/privacy",
        },
    }
