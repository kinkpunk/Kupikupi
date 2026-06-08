import json
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.error_reporting import ErrorReporter, build_error_reporter
from app.core.metrics import metrics_registry

REQUEST_ID_HEADER = "X-Request-ID"
TRACEPARENT_HEADER = "traceparent"
TRACEPARENT_PATTERN = re.compile(
    r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$",
    re.IGNORECASE,
)

logger = logging.getLogger("kupikupi.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, error_reporter: ErrorReporter | None = None) -> None:
        super().__init__(app)
        self._error_reporter = error_reporter or build_error_reporter()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        traceparent = _traceparent_from_headers(request)
        trace_id = _trace_id(traceparent)
        started_at = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            await self._error_reporter.report(
                {
                    "event": "unhandled_exception",
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "traceparent": traceparent,
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            if "response" in locals():
                response.headers[REQUEST_ID_HEADER] = request_id
                response.headers[TRACEPARENT_HEADER] = traceparent
            metrics_registry.record_request(
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            logger.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "trace_id": trace_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                    },
                    separators=(",", ":"),
                )
            )


def _traceparent_from_headers(request: Request) -> str:
    value = request.headers.get(TRACEPARENT_HEADER)
    if value and TRACEPARENT_PATTERN.match(value):
        return value.lower()
    return _new_traceparent()


def _new_traceparent() -> str:
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]
    return f"00-{trace_id}-{span_id}-01"


def _trace_id(traceparent: str) -> str:
    match = TRACEPARENT_PATTERN.match(traceparent)
    if not match:
        return ""
    return match.group(1).lower()
