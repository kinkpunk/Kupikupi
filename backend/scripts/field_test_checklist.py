import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from scripts.staging_preflight import load_env_file, run_preflight

ChecklistStatus = Literal["ok", "warning", "failed"]


@dataclass(frozen=True)
class ChecklistItem:
    name: str
    status: ChecklistStatus
    detail: str


@dataclass(frozen=True)
class FieldTestChecklistReport:
    items: list[ChecklistItem]
    commands: list[str]

    @property
    def passed(self) -> bool:
        return all(item.status != "failed" for item in self.items)


def build_field_test_checklist(
    *,
    backend_env_path: Path,
    bot_env_path: Path,
    webapp_env_path: Path,
    operator_env_path: Path,
) -> FieldTestChecklistReport:
    paths = {
        "backend": backend_env_path,
        "bot": bot_env_path,
        "webapp": webapp_env_path,
        "operator": operator_env_path,
    }
    missing_paths = [f"{name}: {path}" for name, path in paths.items() if not path.exists()]
    items: list[ChecklistItem] = []
    commands = _recommended_commands(operator_env={})

    if missing_paths:
        items.append(
            ChecklistItem(
                name="env-files",
                status="failed",
                detail="Missing env files: " + ", ".join(missing_paths),
            )
        )
        return FieldTestChecklistReport(items=items, commands=commands)

    backend_env = load_env_file(backend_env_path)
    bot_env = load_env_file(bot_env_path)
    webapp_env = load_env_file(webapp_env_path)
    operator_env = load_env_file(operator_env_path)
    commands = _recommended_commands(operator_env=operator_env)

    items.append(ChecklistItem(name="env-files", status="ok", detail="all env files exist"))
    preflight = run_preflight(
        backend_env=backend_env,
        bot_env=bot_env,
        webapp_env=webapp_env,
        operator_env=operator_env,
    )
    if preflight.passed:
        items.append(ChecklistItem(name="staging-preflight", status="ok", detail="passed"))
    else:
        items.append(
            ChecklistItem(
                name="staging-preflight",
                status="failed",
                detail="; ".join(preflight.issues),
            )
        )

    items.extend(_observability_items(backend_env))

    access_token = operator_env.get("KUPIKUPI_ACCESS_TOKEN", "")
    if access_token:
        items.append(
            ChecklistItem(
                name="authenticated-smoke-token",
                status="ok",
                detail="KUPIKUPI_ACCESS_TOKEN is set",
            )
        )
    else:
        items.append(
            ChecklistItem(
                name="authenticated-smoke-token",
                status="warning",
                detail="authenticated smoke will be skipped until KUPIKUPI_ACCESS_TOKEN is set",
            )
        )

    admin_token = operator_env.get("KUPIKUPI_ADMIN_ACCESS_TOKEN", "")
    if admin_token and admin_token != "replace-with-staging-admin-token":
        items.append(
            ChecklistItem(
                name="admin-smoke-token",
                status="ok",
                detail="KUPIKUPI_ADMIN_ACCESS_TOKEN is set",
            )
        )
    else:
        items.append(
            ChecklistItem(
                name="admin-smoke-token",
                status="failed",
                detail="admin smoke requires KUPIKUPI_ADMIN_ACCESS_TOKEN",
            )
        )

    if operator_env.get("KUPIKUPI_CONFIRM_WATCHLIST") == "1":
        items.append(
            ChecklistItem(
                name="watchlist-confirmation-smoke",
                status="ok",
                detail="watchlist confirmation smoke is enabled",
            )
        )
    else:
        items.append(
            ChecklistItem(
                name="watchlist-confirmation-smoke",
                status="warning",
                detail="set KUPIKUPI_CONFIRM_WATCHLIST=1 for full authenticated smoke",
            )
        )

    if operator_env.get("KUPIKUPI_RUN_NOTIFICATION_SMOKE") == "1":
        items.append(
            ChecklistItem(
                name="notification-admin-smoke",
                status="ok",
                detail="notification admin smoke is enabled",
            )
        )
    else:
        items.append(
            ChecklistItem(
                name="notification-admin-smoke",
                status="warning",
                detail="set KUPIKUPI_RUN_NOTIFICATION_SMOKE=1 to smoke notification endpoints",
            )
        )

    return FieldTestChecklistReport(items=items, commands=commands)


def _observability_items(backend_env: dict[str, str]) -> list[ChecklistItem]:
    items: list[ChecklistItem] = []
    if backend_env.get("ERROR_REPORTING_ENABLED") in {"1", "true", "True"} and backend_env.get(
        "ERROR_REPORTING_ENDPOINT_URL"
    ):
        items.append(
            ChecklistItem(
                name="error-reporting",
                status="ok",
                detail=backend_env["ERROR_REPORTING_ENDPOINT_URL"],
            )
        )
    else:
        items.append(
            ChecklistItem(
                name="error-reporting",
                status="failed",
                detail="ERROR_REPORTING_ENABLED and ERROR_REPORTING_ENDPOINT_URL are required",
            )
        )

    dashboard_url = backend_env.get("OBSERVABILITY_DASHBOARD_URL", "")
    if dashboard_url:
        items.append(
            ChecklistItem(
                name="observability-dashboard",
                status="ok",
                detail=dashboard_url,
            )
        )
    else:
        items.append(
            ChecklistItem(
                name="observability-dashboard",
                status="failed",
                detail="OBSERVABILITY_DASHBOARD_URL is required",
            )
        )

    alert_contact_url = backend_env.get("ALERT_CONTACT_URL", "")
    if alert_contact_url:
        items.append(
            ChecklistItem(
                name="alert-contact",
                status="ok",
                detail=alert_contact_url,
            )
        )
    else:
        items.append(
            ChecklistItem(
                name="alert-contact",
                status="failed",
                detail="ALERT_CONTACT_URL is required",
            )
        )
    return items


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Kupikupi closed field-test checklist.")
    parser.add_argument(
        "--env-dir",
        type=Path,
        default=Path("/tmp/kupikupi-staging-env"),
        help="Directory with generated Kupikupi staging env files.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_field_test_checklist(
        backend_env_path=args.env_dir / "kupikupi-backend.env",
        bot_env_path=args.env_dir / "kupikupi-bot.env",
        webapp_env_path=args.env_dir / "kupikupi-webapp.env",
        operator_env_path=args.env_dir / "kupikupi-operator.env",
    )
    if args.json:
        print(
            json.dumps(
                {"passed": report.passed, **asdict(report)},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        _print_human_report(report)
    raise SystemExit(0 if report.passed else 1)


def _print_human_report(report: FieldTestChecklistReport) -> None:
    print("Kupikupi closed field-test checklist:")
    for item in report.items:
        print(f"- {item.name}: {item.status} ({item.detail})")
    print("\nNext commands:")
    for command in report.commands:
        print(f"- {command}")


def _recommended_commands(*, operator_env: dict[str, str]) -> list[str]:
    api_base_url = operator_env.get("KUPIKUPI_API_BASE_URL", "$KUPIKUPI_API_BASE_URL")
    webapp_url = operator_env.get("KUPIKUPI_WEBAPP_URL", "$KUPIKUPI_WEBAPP_URL")
    support_url = operator_env.get("KUPIKUPI_SUPPORT_URL", "$KUPIKUPI_SUPPORT_URL")
    privacy_url = operator_env.get("KUPIKUPI_PRIVACY_URL", "$KUPIKUPI_PRIVACY_URL")
    terms_url = operator_env.get("KUPIKUPI_TERMS_URL", "$KUPIKUPI_TERMS_URL")
    return [
        "python scripts/staging_preflight.py "
        "--backend-env /tmp/kupikupi-staging-env/kupikupi-backend.env "
        "--bot-env /tmp/kupikupi-staging-env/kupikupi-bot.env "
        "--webapp-env /tmp/kupikupi-staging-env/kupikupi-webapp.env "
        "--operator-env /tmp/kupikupi-staging-env/kupikupi-operator.env",
        "python scripts/staging_smoke.py "
        f"--api-base-url {api_base_url} "
        f"--webapp-url {webapp_url} "
        f"--support-url {support_url} "
        f"--privacy-url {privacy_url} "
        f"--terms-url {terms_url}",
        "python scripts/staging_smoke.py "
        f"--api-base-url {api_base_url} "
        f"--webapp-url {webapp_url} "
        '--access-token "$KUPIKUPI_ACCESS_TOKEN" '
        '--admin-access-token "$KUPIKUPI_ADMIN_ACCESS_TOKEN" '
        "--confirm-watchlist "
        "--run-notification-smoke",
        "python scripts/product_duplicates.py "
        f"--api-base-url {api_base_url} "
        '--access-token "$KUPIKUPI_ADMIN_ACCESS_TOKEN" list',
        "python scripts/notifications.py "
        f"--api-base-url {api_base_url} "
        '--access-token "$KUPIKUPI_ADMIN_ACCESS_TOKEN" generate',
        "python scripts/notifications.py "
        f"--api-base-url {api_base_url} "
        '--access-token "$KUPIKUPI_ADMIN_ACCESS_TOKEN" dispatch --limit 100',
    ]


if __name__ == "__main__":
    main()
