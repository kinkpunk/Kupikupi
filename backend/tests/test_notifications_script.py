import json

import httpx

from scripts.notifications import dispatch_notifications_command, generate_notifications_command


def test_notifications_script_generates_notifications(capsys) -> None:
    client = FakeNotificationAdminClient([httpx.Response(200, json={"created": 4, "skipped": 0})])

    exit_code = generate_notifications_command(
        api_base_url="https://api.example.test/v1",
        access_token="admin-token",
        client=client,
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output == {"created": 4, "skipped": 0}
    assert client.requests == [
        {
            "method": "POST",
            "url": "https://api.example.test/v1/admin/notifications/generate",
            "headers": {"Authorization": "Bearer admin-token"},
        }
    ]


def test_notifications_script_dispatches_notifications(capsys) -> None:
    client = FakeNotificationAdminClient(
        [httpx.Response(200, json={"sent": 3, "failed": 0, "skipped": 1})]
    )

    exit_code = dispatch_notifications_command(
        api_base_url="https://api.example.test/v1/",
        access_token="admin-token",
        limit=25,
        client=client,
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output == {"sent": 3, "failed": 0, "skipped": 1}
    assert client.requests == [
        {
            "method": "POST",
            "url": "https://api.example.test/v1/admin/notifications/dispatch?limit=25",
            "headers": {"Authorization": "Bearer admin-token"},
        }
    ]


def test_notifications_script_reports_api_error(capsys) -> None:
    client = FakeNotificationAdminClient([httpx.Response(500, json={"detail": "No bot token"})])

    exit_code = dispatch_notifications_command(
        api_base_url="https://api.example.test/v1",
        access_token="admin-token",
        limit=100,
        client=client,
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert output == {"status_code": 500, "error": {"detail": "No bot token"}}


class FakeNotificationAdminClient:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = responses
        self.requests: list[dict[str, object]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
    ) -> httpx.Response:
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
            }
        )
        if not self._responses:
            raise AssertionError(f"Unexpected request: {method} {url}")
        return self._responses.pop(0)
