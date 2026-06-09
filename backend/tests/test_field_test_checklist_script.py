from pathlib import Path

from scripts.field_test_checklist import build_field_test_checklist
from scripts.staging_env_template import build_staging_env_template


def test_field_test_checklist_passes_with_valid_operator_env(tmp_path) -> None:
    _write_template(
        tmp_path,
        access_token="user-token",
        confirm_watchlist="1",
        run_notification_smoke="1",
    )

    report = _build_report(tmp_path)

    assert report.passed is True
    assert _status_by_name(report)["env-files"] == "ok"
    assert _status_by_name(report)["staging-preflight"] == "ok"
    assert _status_by_name(report)["error-reporting"] == "ok"
    assert _status_by_name(report)["observability-dashboard"] == "ok"
    assert _status_by_name(report)["alert-contact"] == "ok"
    assert _status_by_name(report)["authenticated-smoke-token"] == "ok"
    assert _status_by_name(report)["admin-smoke-token"] == "ok"
    assert _status_by_name(report)["watchlist-confirmation-smoke"] == "ok"
    assert _status_by_name(report)["notification-admin-smoke"] == "ok"
    assert any("scripts/staging_smoke.py" in command for command in report.commands)
    assert any("scripts/notifications.py" in command for command in report.commands)


def test_field_test_checklist_warns_when_user_smoke_token_is_missing(tmp_path) -> None:
    _write_template(tmp_path)

    report = _build_report(tmp_path)

    assert report.passed is True
    assert _status_by_name(report)["authenticated-smoke-token"] == "warning"
    assert _status_by_name(report)["watchlist-confirmation-smoke"] == "warning"
    assert _status_by_name(report)["notification-admin-smoke"] == "warning"


def test_field_test_checklist_fails_when_env_files_are_missing(tmp_path) -> None:
    report = _build_report(tmp_path)

    assert report.passed is False
    assert report.items[0].name == "env-files"
    assert report.items[0].status == "failed"


def test_field_test_checklist_fails_when_admin_token_is_placeholder(tmp_path) -> None:
    _write_template(tmp_path, admin_token="replace-with-staging-admin-token")

    report = _build_report(tmp_path)

    assert report.passed is False
    assert _status_by_name(report)["staging-preflight"] == "failed"
    assert _status_by_name(report)["admin-smoke-token"] == "failed"


def test_field_test_checklist_fails_when_observability_values_are_missing(tmp_path) -> None:
    _write_template(
        tmp_path,
        backend_overrides={
            'ERROR_REPORTING_ENABLED="1"': 'ERROR_REPORTING_ENABLED="0"',
            'ERROR_REPORTING_ENDPOINT_URL="https://errors.example.test/events"': (
                'ERROR_REPORTING_ENDPOINT_URL=""'
            ),
            'OBSERVABILITY_DASHBOARD_URL="https://dashboards.example.test/kupikupi-staging"': (
                'OBSERVABILITY_DASHBOARD_URL=""'
            ),
            'ALERT_CONTACT_URL="mailto:oncall@example.test"': 'ALERT_CONTACT_URL=""',
        },
    )

    report = _build_report(tmp_path)

    assert report.passed is False
    assert _status_by_name(report)["error-reporting"] == "failed"
    assert _status_by_name(report)["observability-dashboard"] == "failed"
    assert _status_by_name(report)["alert-contact"] == "failed"


def _write_template(
    tmp_path: Path,
    *,
    access_token: str = "",
    admin_token: str = "admin-token",
    confirm_watchlist: str = "0",
    run_notification_smoke: str = "0",
    backend_overrides: dict[str, str] | None = None,
) -> None:
    template = build_staging_env_template(
        api_base_url="https://api.staging.kupikupi.example/v1",
        webapp_url="https://app.staging.kupikupi.example",
        telegram_bot_token="bot-token",
        telegram_allowed_user_ids="123,456",
        jwt_secret_key="secret",
        operator_admin_access_token=admin_token,
    )
    operator_env = template.operator_env.replace(
        'KUPIKUPI_ACCESS_TOKEN=""',
        f'KUPIKUPI_ACCESS_TOKEN="{access_token}"',
    ).replace(
        'KUPIKUPI_CONFIRM_WATCHLIST="0"',
        f'KUPIKUPI_CONFIRM_WATCHLIST="{confirm_watchlist}"',
    ).replace(
        'KUPIKUPI_RUN_NOTIFICATION_SMOKE="0"',
        f'KUPIKUPI_RUN_NOTIFICATION_SMOKE="{run_notification_smoke}"',
    )
    backend_env = template.backend_env
    for old, new in (backend_overrides or {}).items():
        backend_env = backend_env.replace(old, new)
    (tmp_path / "kupikupi-backend.env").write_text(backend_env, encoding="utf-8")
    (tmp_path / "kupikupi-bot.env").write_text(template.bot_env, encoding="utf-8")
    (tmp_path / "kupikupi-webapp.env").write_text(template.webapp_env, encoding="utf-8")
    (tmp_path / "kupikupi-operator.env").write_text(operator_env, encoding="utf-8")


def _build_report(tmp_path: Path):
    return build_field_test_checklist(
        backend_env_path=tmp_path / "kupikupi-backend.env",
        bot_env_path=tmp_path / "kupikupi-bot.env",
        webapp_env_path=tmp_path / "kupikupi-webapp.env",
        operator_env_path=tmp_path / "kupikupi-operator.env",
    )


def _status_by_name(report) -> dict[str, str]:
    return {item.name: item.status for item in report.items}
