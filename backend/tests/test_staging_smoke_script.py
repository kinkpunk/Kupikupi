from scripts.staging_smoke import StagingSmokeConfig, run_staging_smoke, smoke_passed


def test_staging_smoke_checks_public_staging_endpoints() -> None:
    client = FakeSmokeClient(
        {
            ("GET", "https://api.example.test/v1/health"): (
                200,
                {"status": "ok", "service": "api"},
            ),
            ("GET", "https://api.example.test/v1/ready"): (200, {"status": "ok"}),
            ("GET", "https://api.example.test/v1/metrics"): (200, {"requests": 3, "routes": {}}),
            ("GET", "https://app.example.test"): (200, {"text": "<html></html>"}),
            ("GET", "https://app.example.test/privacy"): (200, {"text": "<html></html>"}),
            ("GET", "https://app.example.test/terms"): (200, {"text": "<html></html>"}),
        }
    )

    steps = run_staging_smoke(
        StagingSmokeConfig(
            api_base_url="https://api.example.test/v1",
            webapp_url="https://app.example.test",
            support_url="mailto:support@example.test",
            privacy_url="https://app.example.test/privacy",
            terms_url="https://app.example.test/terms",
        ),
        client,
    )

    assert smoke_passed(steps) is True
    assert [step.name for step in steps] == [
        "api-health",
        "api-ready",
        "api-metrics",
        "webapp",
        "support-url",
        "privacy-url",
        "terms-url",
        "authenticated-flow",
        "admin-flow",
    ]
    assert steps[-1].status == "skipped"


def test_staging_smoke_runs_authenticated_flow_with_watchlist_confirmation() -> None:
    client = FakeSmokeClient(
        {
            ("GET", "https://api.example.test/v1/health"): (
                200,
                {"status": "ok", "service": "api"},
            ),
            ("GET", "https://api.example.test/v1/ready"): (200, {"status": "ok"}),
            ("GET", "https://api.example.test/v1/metrics"): (200, {"requests": 3, "routes": {}}),
            ("GET", "https://app.example.test"): (200, {"text": "<html></html>"}),
            ("GET", "https://api.example.test/v1/me"): (200, {"id": "user-1"}),
            ("POST", "https://api.example.test/v1/shopping-requests"): (
                201,
                {"id": "request-1"},
            ),
            (
                "GET",
                "https://api.example.test/v1/shopping-requests/request-1/recommendations",
            ): (200, {"items": [{"id": "recommendation-1"}]}),
            (
                "POST",
                "https://api.example.test/v1/shopping-requests/request-1/watchlist",
            ): (201, {"id": "watchlist-1"}),
        }
    )

    steps = run_staging_smoke(
        StagingSmokeConfig(
            api_base_url="https://api.example.test/v1",
            webapp_url="https://app.example.test",
            access_token="token",
            confirm_watchlist=True,
        ),
        client,
    )

    assert smoke_passed(steps) is True
    assert [step.name for step in steps] == [
        "api-health",
        "api-ready",
        "api-metrics",
        "webapp",
        "support-url",
        "privacy-url",
        "terms-url",
        "auth-me",
        "shopping-request",
        "recommendations",
        "watchlist-confirmation",
        "admin-flow",
    ]
    assert client.requests[-1]["access_token"] == "token"
    assert client.requests[5]["payload"]["text"].startswith("Хочу беговые кроссовки")


def test_staging_smoke_runs_admin_flow() -> None:
    client = FakeSmokeClient(
        {
            ("GET", "https://api.example.test/v1/health"): (
                200,
                {"status": "ok", "service": "api"},
            ),
            ("GET", "https://api.example.test/v1/ready"): (200, {"status": "ok"}),
            ("GET", "https://api.example.test/v1/metrics"): (200, {"requests": 3, "routes": {}}),
            ("GET", "https://app.example.test"): (200, {"text": "<html></html>"}),
            ("GET", "https://api.example.test/v1/admin/sync-runs"): (
                200,
                {"items": [{"id": "sync-run-1"}]},
            ),
            ("GET", "https://api.example.test/v1/admin/product-duplicate-candidates"): (
                200,
                {"items": [{"normalized_identity": "gt-2000 13"}]},
            ),
        }
    )

    steps = run_staging_smoke(
        StagingSmokeConfig(
            api_base_url="https://api.example.test/v1",
            webapp_url="https://app.example.test",
            admin_access_token="admin-token",
        ),
        client,
    )

    assert smoke_passed(steps) is True
    assert [step.name for step in steps] == [
        "api-health",
        "api-ready",
        "api-metrics",
        "webapp",
        "support-url",
        "privacy-url",
        "terms-url",
        "authenticated-flow",
        "admin-sync-runs",
        "admin-duplicate-candidates",
        "admin-notifications",
    ]
    assert client.requests[-2]["access_token"] == "admin-token"
    assert client.requests[-1]["access_token"] == "admin-token"


def test_staging_smoke_runs_notification_admin_flow_when_enabled() -> None:
    client = FakeSmokeClient(
        {
            ("GET", "https://api.example.test/v1/health"): (
                200,
                {"status": "ok", "service": "api"},
            ),
            ("GET", "https://api.example.test/v1/ready"): (200, {"status": "ok"}),
            ("GET", "https://api.example.test/v1/metrics"): (200, {"requests": 3, "routes": {}}),
            ("GET", "https://app.example.test"): (200, {"text": "<html></html>"}),
            ("GET", "https://api.example.test/v1/admin/sync-runs"): (200, {"items": []}),
            ("GET", "https://api.example.test/v1/admin/product-duplicate-candidates"): (
                200,
                {"items": []},
            ),
            ("POST", "https://api.example.test/v1/admin/notifications/generate"): (
                200,
                {"created": 2, "skipped": 1},
            ),
            ("POST", "https://api.example.test/v1/admin/notifications/dispatch?limit=25"): (
                200,
                {"sent": 2, "failed": 0, "skipped": 1},
            ),
        }
    )

    steps = run_staging_smoke(
        StagingSmokeConfig(
            api_base_url="https://api.example.test/v1",
            webapp_url="https://app.example.test",
            admin_access_token="admin-token",
            run_notification_smoke=True,
            notification_dispatch_limit=25,
        ),
        client,
    )

    assert smoke_passed(steps) is True
    assert [step.name for step in steps] == [
        "api-health",
        "api-ready",
        "api-metrics",
        "webapp",
        "support-url",
        "privacy-url",
        "terms-url",
        "authenticated-flow",
        "admin-sync-runs",
        "admin-duplicate-candidates",
        "admin-notifications-generate",
        "admin-notifications-dispatch",
    ]
    assert client.requests[-2]["access_token"] == "admin-token"
    assert client.requests[-1]["access_token"] == "admin-token"


def test_staging_smoke_fails_when_readiness_is_degraded() -> None:
    client = FakeSmokeClient(
        {
            ("GET", "https://api.example.test/v1/health"): (
                200,
                {"status": "ok", "service": "api"},
            ),
            ("GET", "https://api.example.test/v1/ready"): (503, {"status": "degraded"}),
            ("GET", "https://api.example.test/v1/metrics"): (200, {"requests": 3, "routes": {}}),
            ("GET", "https://app.example.test"): (200, {"text": "<html></html>"}),
        }
    )

    steps = run_staging_smoke(
        StagingSmokeConfig(
            api_base_url="https://api.example.test/v1",
            webapp_url="https://app.example.test",
        ),
        client,
    )

    assert smoke_passed(steps) is False
    assert steps[1].name == "api-ready"
    assert steps[1].status == "failed"


def test_staging_smoke_fails_when_configured_privacy_url_is_unavailable() -> None:
    client = FakeSmokeClient(
        {
            ("GET", "https://api.example.test/v1/health"): (
                200,
                {"status": "ok", "service": "api"},
            ),
            ("GET", "https://api.example.test/v1/ready"): (200, {"status": "ok"}),
            ("GET", "https://api.example.test/v1/metrics"): (200, {"requests": 3, "routes": {}}),
            ("GET", "https://app.example.test"): (200, {"text": "<html></html>"}),
            ("GET", "https://app.example.test/privacy"): (404, {"text": "missing"}),
        }
    )

    steps = run_staging_smoke(
        StagingSmokeConfig(
            api_base_url="https://api.example.test/v1",
            webapp_url="https://app.example.test",
            privacy_url="https://app.example.test/privacy",
        ),
        client,
    )

    assert smoke_passed(steps) is False
    assert steps[5].name == "privacy-url"
    assert steps[5].status == "failed"


class FakeSmokeClient:
    def __init__(self, responses):
        self._responses = responses
        self.requests = []

    def request(self, method, url, *, access_token=None, payload=None):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "access_token": access_token,
                "payload": payload,
            }
        )
        key = (method, url)
        if key not in self._responses:
            raise AssertionError(f"Unexpected request: {method} {url}")
        return self._responses[key]
