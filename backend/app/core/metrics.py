from dataclasses import dataclass, field
from threading import Lock


@dataclass
class RouteMetrics:
    requests: int = 0
    total_duration_ms: float = 0.0
    status_counts: dict[str, int] = field(default_factory=dict)


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._routes: dict[str, RouteMetrics] = {}

    def record_request(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        key = f"{method.upper()} {path}"
        status_key = str(status_code)
        with self._lock:
            metrics = self._routes.setdefault(key, RouteMetrics())
            metrics.requests += 1
            metrics.total_duration_ms += duration_ms
            metrics.status_counts[status_key] = metrics.status_counts.get(status_key, 0) + 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            routes = {}
            total_requests = 0
            for key, metrics in self._routes.items():
                total_requests += metrics.requests
                routes[key] = {
                    "requests": metrics.requests,
                    "avg_duration_ms": (
                        round(metrics.total_duration_ms / metrics.requests, 2)
                        if metrics.requests
                        else 0
                    ),
                    "status_counts": dict(metrics.status_counts),
                }
            return {
                "requests": total_requests,
                "routes": routes,
            }

    def reset(self) -> None:
        with self._lock:
            self._routes.clear()


metrics_registry = MetricsRegistry()
