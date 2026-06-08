from scripts.staging_env_template import build_staging_env_template
from scripts.staging_preflight import load_env_file, run_preflight


def test_staging_env_template_contains_matching_service_values(tmp_path) -> None:
    template = build_staging_env_template(
        api_base_url="https://api.staging.kupikupi.example/v1",
        webapp_url="https://app.staging.kupikupi.example",
        telegram_bot_token="token",
        telegram_allowed_user_ids="123,456",
        support_contact_url="mailto:support@example.test",
        privacy_policy_url="https://app.staging.kupikupi.example/privacy",
        terms_url="https://app.staging.kupikupi.example/terms",
        jwt_secret_key="secret",
        operator_admin_access_token="staging-admin-token",
    )

    backend_path = tmp_path / "backend.env"
    bot_path = tmp_path / "bot.env"
    webapp_path = tmp_path / "webapp.env"
    operator_path = tmp_path / "operator.env"
    backend_path.write_text(template.backend_env, encoding="utf-8")
    bot_path.write_text(template.bot_env, encoding="utf-8")
    webapp_path.write_text(template.webapp_env, encoding="utf-8")
    operator_path.write_text(template.operator_env, encoding="utf-8")

    report = run_preflight(
        backend_env=load_env_file(backend_path),
        bot_env=load_env_file(bot_path),
        webapp_env=load_env_file(webapp_path),
        operator_env=load_env_file(operator_path),
    )

    assert report.passed is True
    assert "CORS_ALLOWED_ORIGINS=\"https://app.staging.kupikupi.example\"" in template.backend_env
    assert "TELEGRAM_ALLOWED_USER_IDS=\"123,456\"" in template.bot_env
    assert 'BOT_RUN_MODE="polling"' in template.bot_env
    assert 'TERMS_URL="https://app.staging.kupikupi.example/terms"' in template.bot_env
    assert (
        'NEXT_PUBLIC_TERMS_URL="https://app.staging.kupikupi.example/terms"'
        in template.webapp_env
    )
    assert (
        'KUPIKUPI_API_BASE_URL="https://api.staging.kupikupi.example/v1"'
        in template.operator_env
    )
    assert 'KUPIKUPI_WEBAPP_URL="https://app.staging.kupikupi.example"' in template.operator_env
    assert 'KUPIKUPI_ADMIN_ACCESS_TOKEN="staging-admin-token"' in template.operator_env
    assert (
        'OBSERVABILITY_DASHBOARD_URL="https://dashboards.example.test/kupikupi-staging"'
        in template.backend_env
    )
    assert 'ALERT_CONTACT_URL="mailto:oncall@example.test"' in template.backend_env


def test_staging_env_template_allows_error_reporting_endpoint_override() -> None:
    template = build_staging_env_template(
        api_base_url="https://api.staging.kupikupi.example/v1",
        webapp_url="https://app.staging.kupikupi.example",
        error_reporting_endpoint_url="https://errors.example.test/events",
    )

    assert 'ERROR_REPORTING_ENABLED="1"' in template.backend_env
    assert (
        'ERROR_REPORTING_ENDPOINT_URL="https://errors.example.test/events"'
        in template.backend_env
    )


def test_staging_env_template_supports_webhook_bot_mode(tmp_path) -> None:
    template = build_staging_env_template(
        api_base_url="https://api.staging.kupikupi.example/v1",
        webapp_url="https://app.staging.kupikupi.example",
        bot_run_mode="webhook",
        telegram_webhook_url="https://bot.staging.kupikupi.example/telegram/webhook",
        telegram_webhook_secret="secret",
    )

    bot_path = tmp_path / "bot.env"
    bot_path.write_text(template.bot_env, encoding="utf-8")

    assert 'BOT_RUN_MODE="webhook"' in template.bot_env
    assert (
        'TELEGRAM_WEBHOOK_URL="https://bot.staging.kupikupi.example/telegram/webhook"'
        in template.bot_env
    )
    assert 'TELEGRAM_WEBHOOK_SECRET="secret"' in template.bot_env
