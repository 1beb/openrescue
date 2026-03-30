from prometheus_client import CollectorRegistry, Counter, Gauge, start_http_server

REGISTRY = CollectorRegistry()


class MetricsCollector:
    def __init__(self, registry: CollectorRegistry | None = None):
        self.registry = registry or REGISTRY
        self.active_seconds = Counter(
            "openrescue_active_seconds_total",
            "Total active seconds per app/project/category",
            ["app", "project", "category"],
            registry=self.registry,
        )
        self.idle_seconds = Gauge(
            "openrescue_idle_seconds",
            "Current idle time in seconds",
            registry=self.registry,
        )

    def record_activity(self, app: str, project: str, category: str, seconds: float) -> None:
        self.active_seconds.labels(app=app, project=project, category=category).inc(seconds)

    def record_idle(self, seconds: float) -> None:
        self.idle_seconds.set(seconds)

    def start_server(self, port: int = 8000) -> None:
        start_http_server(port, registry=self.registry)
