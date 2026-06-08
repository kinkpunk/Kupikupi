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
        jwt_secret_key="secret",
    )

    backend_path = tmp_path / "backend.env"
    bot_path = tmp_path / "bot.env"
    webapp_path = tmp_path / "webapp.env"
    backend_path.write_text(template.backend_env, encoding="utf-8")
    bot_path.write_text(template.bot_env, encoding="utf-8")
    webapp_path.write_text(template.webapp_env, encoding="utf-8")

    report = run_preflight(
        backend_env=load_env_file(backend_path),
        bot_env=load_env_file(bot_path),
        webapp_env=load_env_file(webapp_path),
    )

    assert report.passed is True
    assert "CORS_ALLOWED_ORIGINS=\"https://app.staging.kupikupi.example\"" in template.backend_env
    assert "TELEGRAM_ALLOWED_USER_IDS=\"123,456\"" in template.bot_env
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
