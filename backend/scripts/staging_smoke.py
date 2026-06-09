import argparse
import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

DEFAULT_REQUEST_TEXT = (
    "Хочу беговые кроссовки для ежедневных тренировок. Размер 41. Бюджет 150 евро."
)


@dataclass(frozen=True)
class StagingSmokeConfig:
    api_base_url: str
    webapp_url: str
    support_url: str | None = None
    privacy_url: str | None = None
    terms_url: str | None = None
    access_token: str | None = None
    admin_access_token: str | None = None
    request_text: str = DEFAULT_REQUEST_TEXT
    confirm_watchlist: bool = False
    run_notification_smoke: bool = False
    notification_dispatch_limit: int = 100


@dataclass(frozen=True)
class SmokeStep:
    name: str
    status: str
    detail: str


class HttpClient(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        access_token: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, Any]:
        pass


class UrlopenHttpClient:
    def request(
        self,
        method: str,
        url: str,
        *,
        access_token: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, Any]:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=15) as response:
                raw = response.read().decode("utf-8")
                return response.status, _decode_body(raw)
        except HTTPError as exc:
            raw = exc.read().decode("utf-8")
            return exc.code, _decode_body(raw)
        except URLError as exc:
            raise RuntimeError(f"{url} is unreachable: {exc}") from exc


def run_staging_smoke(config: StagingSmokeConfig, client: HttpClient) -> list[SmokeStep]:
    steps = [
        _check_api_health(config, client),
        _check_api_readiness(config, client),
        _check_api_metrics(config, client),
        _check_webapp(config, client),
        _check_optional_url("support-url", config.support_url, client),
        _check_optional_url("privacy-url", config.privacy_url, client),
        _check_optional_url("terms-url", config.terms_url, client),
    ]

    if config.access_token:
        steps.extend(_run_authenticated_flow(config, client))
    else:
        steps.append(SmokeStep("authenticated-flow", "skipped", "KUPIKUPI_ACCESS_TOKEN is empty."))

    if config.admin_access_token:
        steps.extend(_run_admin_flow(config, client))
    else:
        steps.append(SmokeStep("admin-flow", "skipped", "KUPIKUPI_ADMIN_ACCESS_TOKEN is empty."))

    return steps


def print_report(steps: list[SmokeStep]) -> None:
    print("Kupikupi staging smoke report:")
    for step in steps:
        print(f"- {step.name}: {step.status} ({step.detail})")


def smoke_passed(steps: list[SmokeStep]) -> bool:
    return all(step.status in {"ok", "skipped"} for step in steps)


def config_from_env() -> StagingSmokeConfig:
    api_base_url = os.environ.get("KUPIKUPI_API_BASE_URL", "").strip()
    webapp_url = os.environ.get("KUPIKUPI_WEBAPP_URL", "").strip()
    if not api_base_url:
        raise ValueError("KUPIKUPI_API_BASE_URL is required.")
    if not webapp_url:
        raise ValueError("KUPIKUPI_WEBAPP_URL is required.")
    return StagingSmokeConfig(
        api_base_url=api_base_url,
        webapp_url=webapp_url,
        support_url=os.environ.get("KUPIKUPI_SUPPORT_URL") or None,
        privacy_url=os.environ.get("KUPIKUPI_PRIVACY_URL") or None,
        terms_url=os.environ.get("KUPIKUPI_TERMS_URL") or None,
        access_token=os.environ.get("KUPIKUPI_ACCESS_TOKEN") or None,
        admin_access_token=os.environ.get("KUPIKUPI_ADMIN_ACCESS_TOKEN") or None,
        request_text=os.environ.get("KUPIKUPI_SMOKE_REQUEST_TEXT", DEFAULT_REQUEST_TEXT),
        confirm_watchlist=os.environ.get("KUPIKUPI_CONFIRM_WATCHLIST") == "1",
        run_notification_smoke=os.environ.get("KUPIKUPI_RUN_NOTIFICATION_SMOKE") == "1",
        notification_dispatch_limit=int(
            os.environ.get("KUPIKUPI_NOTIFICATION_DISPATCH_LIMIT", "100")
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a remote Kupikupi staging smoke check.")
    parser.add_argument("--api-base-url", default=os.environ.get("KUPIKUPI_API_BASE_URL", ""))
    parser.add_argument("--webapp-url", default=os.environ.get("KUPIKUPI_WEBAPP_URL", ""))
    parser.add_argument("--support-url", default=os.environ.get("KUPIKUPI_SUPPORT_URL"))
    parser.add_argument("--privacy-url", default=os.environ.get("KUPIKUPI_PRIVACY_URL"))
    parser.add_argument("--terms-url", default=os.environ.get("KUPIKUPI_TERMS_URL"))
    parser.add_argument("--access-token", default=os.environ.get("KUPIKUPI_ACCESS_TOKEN"))
    parser.add_argument(
        "--admin-access-token",
        default=os.environ.get("KUPIKUPI_ADMIN_ACCESS_TOKEN"),
    )
    parser.add_argument(
        "--request-text",
        default=os.environ.get("KUPIKUPI_SMOKE_REQUEST_TEXT", DEFAULT_REQUEST_TEXT),
    )
    parser.add_argument(
        "--confirm-watchlist",
        action="store_true",
        default=os.environ.get("KUPIKUPI_CONFIRM_WATCHLIST") == "1",
    )
    parser.add_argument(
        "--run-notification-smoke",
        action="store_true",
        default=os.environ.get("KUPIKUPI_RUN_NOTIFICATION_SMOKE") == "1",
    )
    parser.add_argument(
        "--notification-dispatch-limit",
        type=int,
        default=int(os.environ.get("KUPIKUPI_NOTIFICATION_DISPATCH_LIMIT", "100")),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = StagingSmokeConfig(
        api_base_url=args.api_base_url.strip(),
        webapp_url=args.webapp_url.strip(),
        support_url=args.support_url or None,
        privacy_url=args.privacy_url or None,
        terms_url=args.terms_url or None,
        access_token=args.access_token or None,
        admin_access_token=args.admin_access_token or None,
        request_text=args.request_text,
        confirm_watchlist=args.confirm_watchlist,
        run_notification_smoke=args.run_notification_smoke,
        notification_dispatch_limit=args.notification_dispatch_limit,
    )
    if not config.api_base_url or not config.webapp_url:
        print("Provide --api-base-url and --webapp-url or matching KUPIKUPI_* env vars.")
        raise SystemExit(2)

    steps = run_staging_smoke(config, UrlopenHttpClient())
    print_report(steps)
    raise SystemExit(0 if smoke_passed(steps) else 1)


def _check_api_health(config: StagingSmokeConfig, client: HttpClient) -> SmokeStep:
    status, body = client.request("GET", _api_url(config, "/health"))
    if status == 200 and body.get("status") == "ok":
        return SmokeStep("api-health", "ok", body.get("service", "backend"))
    return SmokeStep("api-health", "failed", f"HTTP {status}: {body}")


def _check_api_readiness(config: StagingSmokeConfig, client: HttpClient) -> SmokeStep:
    status, body = client.request("GET", _api_url(config, "/ready"))
    if status == 200 and body.get("status") == "ok":
        return SmokeStep("api-ready", "ok", "dependencies ok")
    return SmokeStep("api-ready", "failed", f"HTTP {status}: {body}")


def _check_api_metrics(config: StagingSmokeConfig, client: HttpClient) -> SmokeStep:
    status, body = client.request("GET", _api_url(config, "/metrics"))
    if status == 200 and "requests" in body:
        return SmokeStep("api-metrics", "ok", f"{body.get('requests')} requests counted")
    return SmokeStep("api-metrics", "failed", f"HTTP {status}: {body}")


def _check_webapp(config: StagingSmokeConfig, client: HttpClient) -> SmokeStep:
    status, _body = client.request("GET", config.webapp_url)
    if status == 200:
        return SmokeStep("webapp", "ok", config.webapp_url)
    return SmokeStep("webapp", "failed", f"HTTP {status}")


def _check_optional_url(name: str, url: str | None, client: HttpClient) -> SmokeStep:
    if not url:
        return SmokeStep(name, "skipped", "URL is not configured.")
    if urlparse(url).scheme == "mailto":
        return SmokeStep(name, "ok", "mailto link configured")
    status, _body = client.request("GET", url)
    if 200 <= status < 400:
        return SmokeStep(name, "ok", url)
    return SmokeStep(name, "failed", f"HTTP {status}: {url}")


def _run_authenticated_flow(config: StagingSmokeConfig, client: HttpClient) -> list[SmokeStep]:
    steps = []
    status, user = client.request(
        "GET",
        _api_url(config, "/me"),
        access_token=config.access_token,
    )
    if status == 200 and user.get("id"):
        steps.append(SmokeStep("auth-me", "ok", f"user {user['id']}"))
    else:
        steps.append(SmokeStep("auth-me", "failed", f"HTTP {status}: {user}"))
        return steps

    status, request = client.request(
        "POST",
        _api_url(config, "/shopping-requests"),
        access_token=config.access_token,
        payload={"text": config.request_text},
    )
    request_id = request.get("id") if isinstance(request, dict) else None
    if status == 201 and request_id:
        steps.append(SmokeStep("shopping-request", "ok", f"request {request_id}"))
    else:
        steps.append(SmokeStep("shopping-request", "failed", f"HTTP {status}: {request}"))
        return steps

    status, recommendations = client.request(
        "GET",
        _api_url(config, f"/shopping-requests/{request_id}/recommendations"),
        access_token=config.access_token,
    )
    items = recommendations.get("items", []) if isinstance(recommendations, dict) else []
    if status == 200:
        steps.append(SmokeStep("recommendations", "ok", f"{len(items)} items"))
    else:
        steps.append(SmokeStep("recommendations", "failed", f"HTTP {status}: {recommendations}"))
        return steps

    if not config.confirm_watchlist:
        steps.append(
            SmokeStep(
                "watchlist-confirmation",
                "skipped",
                "enable with --confirm-watchlist",
            )
        )
        return steps

    status, watchlist = client.request(
        "POST",
        _api_url(config, f"/shopping-requests/{request_id}/watchlist"),
        access_token=config.access_token,
    )
    if status == 201 and isinstance(watchlist, dict) and watchlist.get("id"):
        steps.append(SmokeStep("watchlist-confirmation", "ok", f"watchlist {watchlist['id']}"))
    else:
        steps.append(SmokeStep("watchlist-confirmation", "failed", f"HTTP {status}: {watchlist}"))
    return steps


def _run_admin_flow(config: StagingSmokeConfig, client: HttpClient) -> list[SmokeStep]:
    steps = []
    status, sync_runs = client.request(
        "GET",
        _api_url(config, "/admin/sync-runs"),
        access_token=config.admin_access_token,
    )
    if status == 200 and isinstance(sync_runs, dict) and "items" in sync_runs:
        steps.append(SmokeStep("admin-sync-runs", "ok", f"{len(sync_runs['items'])} runs"))
    else:
        steps.append(SmokeStep("admin-sync-runs", "failed", f"HTTP {status}: {sync_runs}"))
        return steps

    status, candidates = client.request(
        "GET",
        _api_url(config, "/admin/product-duplicate-candidates"),
        access_token=config.admin_access_token,
    )
    if status == 200 and isinstance(candidates, dict) and "items" in candidates:
        steps.append(
            SmokeStep(
                "admin-duplicate-candidates",
                "ok",
                f"{len(candidates['items'])} groups",
            )
        )
    else:
        steps.append(
            SmokeStep(
                "admin-duplicate-candidates",
                "failed",
                f"HTTP {status}: {candidates}",
            )
        )
    steps.extend(_run_notification_admin_flow(config, client))
    return steps


def _run_notification_admin_flow(
    config: StagingSmokeConfig,
    client: HttpClient,
) -> list[SmokeStep]:
    if not config.run_notification_smoke:
        return [
            SmokeStep(
                "admin-notifications",
                "skipped",
                "enable with --run-notification-smoke",
            )
        ]

    steps = []
    status, generation = client.request(
        "POST",
        _api_url(config, "/admin/notifications/generate"),
        access_token=config.admin_access_token,
    )
    if status == 200 and isinstance(generation, dict) and "created" in generation:
        steps.append(
            SmokeStep(
                "admin-notifications-generate",
                "ok",
                f"{generation.get('created')} created, {generation.get('skipped')} skipped",
            )
        )
    else:
        steps.append(
            SmokeStep(
                "admin-notifications-generate",
                "failed",
                f"HTTP {status}: {generation}",
            )
        )
        return steps

    status, dispatch = client.request(
        "POST",
        _api_url(
            config,
            f"/admin/notifications/dispatch?limit={config.notification_dispatch_limit}",
        ),
        access_token=config.admin_access_token,
    )
    if status == 200 and isinstance(dispatch, dict) and "sent" in dispatch:
        steps.append(
            SmokeStep(
                "admin-notifications-dispatch",
                "ok",
                (
                    f"{dispatch.get('sent')} sent, {dispatch.get('failed')} failed, "
                    f"{dispatch.get('skipped')} skipped"
                ),
            )
        )
    else:
        steps.append(
            SmokeStep(
                "admin-notifications-dispatch",
                "failed",
                f"HTTP {status}: {dispatch}",
            )
        )
    return steps


def _api_url(config: StagingSmokeConfig, path: str) -> str:
    base = config.api_base_url.rstrip("/") + "/"
    return urljoin(base, path.lstrip("/"))


def _decode_body(raw: str) -> Any:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"text": raw[:500]}


if __name__ == "__main__":
    main()
