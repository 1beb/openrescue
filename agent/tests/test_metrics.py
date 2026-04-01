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


def test_record_pulse():
    registry = CollectorRegistry()
    collector = MetricsCollector(registry=registry)

    collector.record_pulse(75.0)

    value = registry.get_sample_value("openrescue_productivity_pulse")
    assert value == 75.0


def test_calculate_pulse_all_very_productive():
    registry = CollectorRegistry()
    collector = MetricsCollector(registry=registry)

    collector.record_activity(app="Code", project="test", category="very_productive", seconds=100.0)
    pulse = collector.calculate_pulse()
    assert pulse == 100.0


def test_calculate_pulse_mixed():
    registry = CollectorRegistry()
    collector = MetricsCollector(registry=registry)

    collector.record_activity(app="Code", project="test", category="very_productive", seconds=50.0)
    collector.record_activity(app="Reddit", project="test", category="very_distracting", seconds=50.0)
    pulse = collector.calculate_pulse()
    assert pulse == 50.0


def test_calculate_pulse_all_very_distracting():
    registry = CollectorRegistry()
    collector = MetricsCollector(registry=registry)

    collector.record_activity(app="Reddit", project="test", category="very_distracting", seconds=100.0)
    pulse = collector.calculate_pulse()
    assert pulse == 0.0


def test_calculate_pulse_no_data():
    registry = CollectorRegistry()
    collector = MetricsCollector(registry=registry)

    pulse = collector.calculate_pulse()
    assert pulse == 0.0
