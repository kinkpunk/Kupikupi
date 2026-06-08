from fastapi.testclient import TestClient

from app.api.v1 import health
from app.core.config import settings
from app.core.metrics import metrics_registry
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


def test_request_id_header_is_preserved() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/health", headers={"X-Request-ID": "request-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "request-123"


def test_request_id_header_is_generated() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]


def test_traceparent_header_is_preserved() -> None:
    client = TestClient(create_app())
    traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"

    response = client.get("/v1/health", headers={"traceparent": traceparent})

    assert response.status_code == 200
    assert response.headers["traceparent"] == traceparent


def test_traceparent_header_is_generated() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/health")

    assert response.status_code == 200
    parts = response.headers["traceparent"].split("-")
    assert parts[0] == "00"
    assert len(parts[1]) == 32
    assert len(parts[2]) == 16
    assert parts[3] == "01"


def test_metrics_records_requests() -> None:
    metrics_registry.reset()
    client = TestClient(create_app())

    client.get("/v1/health")
    client.get("/v1/health")
    response = client.get("/v1/metrics")

    assert response.status_code == 200
    body = response.json()
    assert body["requests"] >= 2
    assert body["routes"]["GET /v1/health"]["requests"] == 2
    assert body["routes"]["GET /v1/health"]["status_counts"]["200"] == 2
    assert body["routes"]["GET /v1/health"]["avg_duration_ms"] >= 0


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
            "configuration": {"status": "ok", "message": None},
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
            "configuration": {"status": "ok", "message": None},
            "database": {"status": "ok", "message": None},
            "redis": {"status": "error", "message": "redis unavailable"},
        },
    }


def test_readiness_returns_503_for_default_secret_in_production(monkeypatch) -> None:
    async def check_ok() -> health.DependencyHealth:
        return health.DependencyHealth(status="ok")

    original_environment = settings.environment
    original_secret = settings.jwt_secret_key
    settings.environment = "production"
    settings.jwt_secret_key = "change-me-in-production"
    monkeypatch.setattr(health, "check_database", check_ok)
    monkeypatch.setattr(health, "check_redis", check_ok)
    client = TestClient(create_app())

    try:
        response = client.get("/v1/ready")
    finally:
        settings.environment = original_environment
        settings.jwt_secret_key = original_secret

    assert response.status_code == 503
    configuration = response.json()["dependencies"]["configuration"]
    assert configuration["status"] == "error"
    assert "JWT_SECRET_KEY must be changed" in configuration["message"]


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
