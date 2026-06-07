from fastapi import APIRouter, Response
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import settings
from app.db.session import async_session_factory

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class DependencyHealth(BaseModel):
    status: str
    message: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    service: str
    version: str
    dependencies: dict[str, DependencyHealth]


@router.get("/health", response_model=HealthResponse)
async def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok", service="kupikupi-backend", version="0.1.0")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
async def readiness(response: Response) -> ReadinessResponse:
    dependencies = {
        "database": await check_database(),
        "redis": await check_redis(),
    }
    is_ready = all(dependency.status == "ok" for dependency in dependencies.values())
    if not is_ready:
        response.status_code = 503

    return ReadinessResponse(
        status="ok" if is_ready else "degraded",
        service="kupikupi-backend",
        version="0.1.0",
        dependencies=dependencies,
    )


async def check_database() -> DependencyHealth:
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        return DependencyHealth(status="error", message=str(exc))

    return DependencyHealth(status="ok")


async def check_redis() -> DependencyHealth:
    redis = Redis.from_url(settings.redis_url)
    try:
        await redis.ping()
    except Exception as exc:
        return DependencyHealth(status="error", message=str(exc))
    finally:
        await redis.aclose()

    return DependencyHealth(status="ok")
