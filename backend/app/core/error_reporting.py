import logging
from typing import Protocol

import httpx

from app.core.config import settings

logger = logging.getLogger("kupikupi.errors")


class ErrorReporter(Protocol):
    async def report(self, payload: dict[str, object]) -> None:
        pass


class NoopErrorReporter:
    async def report(self, payload: dict[str, object]) -> None:
        return None


class HttpErrorReporter:
    def __init__(self, *, endpoint_url: str) -> None:
        self._endpoint_url = endpoint_url

    async def report(self, payload: dict[str, object]) -> None:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(self._endpoint_url, json=payload)
                response.raise_for_status()
        except Exception as exc:
            logger.warning("Error reporting failed: %s", exc)


def build_error_reporter() -> ErrorReporter:
    if not settings.error_reporting_enabled or not settings.error_reporting_endpoint_url:
        return NoopErrorReporter()
    return HttpErrorReporter(endpoint_url=settings.error_reporting_endpoint_url)
