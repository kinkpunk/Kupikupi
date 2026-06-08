import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.error_reporting import HttpErrorReporter, NoopErrorReporter, build_error_reporter
from app.core.middleware import RequestLoggingMiddleware


class RecordingReporter:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    async def report(self, payload: dict[str, object]) -> None:
        self.payloads.append(payload)


def test_build_error_reporter_defaults_to_noop() -> None:
    reporter = build_error_reporter()

    assert isinstance(reporter, NoopErrorReporter)


def test_http_error_reporter_can_be_constructed() -> None:
    reporter = HttpErrorReporter(endpoint_url="https://errors.example.test/events")

    assert reporter is not None


def test_request_logging_middleware_reports_unhandled_exceptions() -> None:
    reporter = RecordingReporter()
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware, error_reporter=reporter)

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"

    response = client.get(
        "/boom",
        headers={"X-Request-ID": "request-err-1", "traceparent": traceparent},
    )

    assert response.status_code == 500
    assert reporter.payloads == [
        {
            "event": "unhandled_exception",
            "request_id": "request-err-1",
            "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
            "traceparent": traceparent,
            "method": "GET",
            "path": "/boom",
            "error_type": "RuntimeError",
            "error_message": "boom",
        }
    ]


@pytest.mark.asyncio
async def test_noop_error_reporter_ignores_payload() -> None:
    await NoopErrorReporter().report({"event": "test"})
