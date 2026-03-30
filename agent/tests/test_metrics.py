from prometheus_client import CollectorRegistry
from openrescue.metrics import MetricsCollector


def test_record_activity_increments_counter():
    registry = CollectorRegistry()
    collector = MetricsCollector(registry=registry)

    collector.record_activity(app="Code", project="openrescue", category="productive", seconds=5.0)
    collector.record_activity(app="Code", project="openrescue", category="productive", seconds=5.0)

    value = registry.get_sample_value(
        "openrescue_active_seconds_total",
        {"app": "Code", "project": "openrescue", "category": "productive"},
    )
    assert value == 10.0


def test_record_idle():
    registry = CollectorRegistry()
    collector = MetricsCollector(registry=registry)

    collector.record_idle(seconds=120.0)

    value = registry.get_sample_value("openrescue_idle_seconds")
    assert value == 120.0
