from fastapi.testclient import TestClient

from app.api.v1 import health
from app.main import create_app


def test_healthcheck_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "kupikupi-backend",
        "version": "0.1.0",
    }


def test_readiness_returns_ok_when_dependencies_are_available(monkeypatch) -> None:
    async def check_ok() -> health.DependencyHealth:
        return health.DependencyHealth(status="ok")

    monkeypatch.setattr(health, "check_database", check_ok)
    monkeypatch.setattr(health, "check_redis", check_ok)
    client = TestClient(create_app())

    response = client.get("/v1/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "kupikupi-backend",
        "version": "0.1.0",
        "dependencies": {
            "database": {"status": "ok", "message": None},
            "redis": {"status": "ok", "message": None},
        },
    }


def test_readiness_returns_503_when_dependency_fails(monkeypatch) -> None:
    async def check_database_ok() -> health.DependencyHealth:
        return health.DependencyHealth(status="ok")

    async def check_redis_error() -> health.DependencyHealth:
        return health.DependencyHealth(status="error", message="redis unavailable")

    monkeypatch.setattr(health, "check_database", check_database_ok)
    monkeypatch.setattr(health, "check_redis", check_redis_error)
    client = TestClient(create_app())

    response = client.get("/v1/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "service": "kupikupi-backend",
        "version": "0.1.0",
        "dependencies": {
            "database": {"status": "ok", "message": None},
            "redis": {"status": "error", "message": "redis unavailable"},
        },
    }


def test_cors_allows_webapp_origin() -> None:
    client = TestClient(create_app())

    response = client.options(
        "/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
