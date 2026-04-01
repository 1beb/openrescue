from prometheus_client import CollectorRegistry, Counter, Gauge, start_http_server

REGISTRY = CollectorRegistry()

CATEGORY_WEIGHTS = {
    "very_productive": 4,
    "productive": 3,
    "uncategorized": 2,
    "distracting": 1,
    "very_distracting": 0,
}


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
        self.productivity_pulse = Gauge(
            "openrescue_productivity_pulse",
            "Productivity pulse score 0-100",
            registry=self.registry,
        )
        self._category_totals: dict[str, float] = {k: 0.0 for k in CATEGORY_WEIGHTS}

    def record_activity(self, app: str, project: str, category: str, seconds: float) -> None:
        self.active_seconds.labels(app=app, project=project, category=category).inc(seconds)
        if category in self._category_totals:
            self._category_totals[category] += seconds

    def record_idle(self, seconds: float) -> None:
        self.idle_seconds.set(seconds)

    def record_pulse(self, pulse: float) -> None:
        self.productivity_pulse.set(pulse)

    def calculate_pulse(self) -> float:
        total = sum(self._category_totals.values())
        if total == 0:
            return 0.0
        weighted = sum(
            self._category_totals[cat] * weight
            for cat, weight in CATEGORY_WEIGHTS.items()
        )
        return (weighted / (total * 4)) * 100

    def start_server(self, port: int = 8000) -> None:
        start_http_server(port, registry=self.registry)
