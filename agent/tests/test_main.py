import time
from unittest.mock import MagicMock
from openrescue.main import tracking_loop
from openrescue.config import Config, ServerConfig, TrackingConfig, ProjectsConfig, CategoriesConfig
from openrescue.tracker import ActivityEvent


def _make_config(**overrides):
    return Config(
        server=ServerConfig(loki_url="http://localhost:3100", mimir_url="http://localhost:9009"),
        tracking=TrackingConfig(poll_interval_seconds=5, **overrides),
        projects=ProjectsConfig(base_paths=["~/projects"]),
        categories=CategoriesConfig(very_productive=["code"], productive=[], distracting=[], very_distracting=[]),
    )


def test_session_emitted_on_window_change(mocker):
    mocker.patch("time.sleep")
    events = [
        ActivityEvent(time.time(), "main.py - openrescue - Visual Studio Code", "Code",
                      1234, "/home/b/projects/openrescue", None),
        ActivityEvent(time.time(), "main.py - openrescue - Visual Studio Code", "Code",
                      1234, "/home/b/projects/openrescue", None),
        ActivityEvent(time.time(), "Google - Firefox", "Firefox",
                      5678, "/home/b", None),
    ]
    call_count = [0]

    def mock_get_window():
        e = events[call_count[0]]
        call_count[0] += 1
        return e

    mocker.patch("openrescue.main.get_active_window", side_effect=mock_get_window)
    mocker.patch("openrescue.main.get_idle_time", return_value=0.0)

    mock_shipper = MagicMock()
    mock_metrics = MagicMock()

    tracking_loop(_make_config(), mock_shipper, mock_metrics, hostname="test", max_iterations=3)

    # Session 1 (Code) flushed when window changed to Firefox
    # Session 2 (Firefox) flushed at end of loop
    assert mock_shipper.push_session.call_count == 2
    first_call = mock_shipper.push_session.call_args_list[0]
    assert first_call[1]["hostname"] == "test"
    assert first_call[0][0].app_name == "Code"


def test_idle_suppresses_events(mocker):
    mocker.patch("time.sleep")
    event = ActivityEvent(time.time(), "Slack", "Slack", 1234, "/home/b", None)

    mocker.patch("openrescue.main.get_active_window", return_value=event)
    mocker.patch("openrescue.main.get_idle_time", return_value=600.0)

    mock_shipper = MagicMock()
    mock_metrics = MagicMock()

    tracking_loop(_make_config(), mock_shipper, mock_metrics, hostname="test", max_iterations=3)

    mock_shipper.push_session.assert_not_called()
    mock_metrics.record_activity.assert_not_called()


def test_project_detected_from_cwd(mocker):
    mocker.patch("time.sleep")
    event = ActivityEvent(time.time(), "main.py - openrescue - Visual Studio Code", "Code",
                          1234, "/home/b/projects/openrescue", None)

    mocker.patch("openrescue.main.get_active_window", return_value=event)
    mocker.patch("openrescue.main.get_idle_time", return_value=0.0)

    mock_shipper = MagicMock()
    mock_metrics = MagicMock()

    tracking_loop(_make_config(), mock_shipper, mock_metrics, hostname="test", max_iterations=2)

    # Flushed at end
    assert mock_shipper.push_session.call_count == 1
    pushed_event = mock_shipper.push_session.call_args[0][0]
    assert pushed_event.project == "openrescue"


def test_pulse_recorded_on_session_flush(mocker):
    mocker.patch("time.sleep")
    events = [
        ActivityEvent(time.time(), "main.py - VS Code", "Code",
                      1234, "/home/b/projects/openrescue", None),
        ActivityEvent(time.time(), "Google - Firefox", "Firefox",
                      5678, "/home/b", None),
    ]
    call_count = [0]

    def mock_get_window():
        e = events[call_count[0]]
        call_count[0] += 1
        return e

    mocker.patch("openrescue.main.get_active_window", side_effect=mock_get_window)
    mocker.patch("openrescue.main.get_idle_time", return_value=0.0)

    mock_shipper = MagicMock()
    mock_metrics = MagicMock()
    mock_metrics.calculate_pulse.return_value = 75.0

    config = _make_config()
    tracking_loop(config, mock_shipper, mock_metrics, hostname="test", max_iterations=2)

    mock_metrics.calculate_pulse.assert_called()
    mock_metrics.record_pulse.assert_called_with(75.0)


def test_session_buffered_before_shipping(mocker):
    mocker.patch("time.sleep")
    events = [
        ActivityEvent(time.time(), "main.py - VS Code", "Code",
                      1234, "/home/b/projects/openrescue", None),
        ActivityEvent(time.time(), "Google - Firefox", "Firefox",
                      5678, "/home/b", None),
    ]
    call_count = [0]

    def mock_get_window():
        e = events[call_count[0]]
        call_count[0] += 1
        return e

    mocker.patch("openrescue.main.get_active_window", side_effect=mock_get_window)
    mocker.patch("openrescue.main.get_idle_time", return_value=0.0)

    mock_shipper = MagicMock()
    mock_metrics = MagicMock()
    mock_metrics.calculate_pulse.return_value = 50.0
    mock_buffer = MagicMock()
    mock_buffer.get_unshipped.return_value = []

    config = _make_config()
    tracking_loop(config, mock_shipper, mock_metrics, hostname="test",
                  max_iterations=2, buffer=mock_buffer)

    mock_buffer.insert.assert_called()
    # First insert is the Code session (flushed on window change)
    insert_data = mock_buffer.insert.call_args_list[0][0][0]
    assert insert_data["app_name"] == "Code"
    assert insert_data["hostname"] == "test"
    assert insert_data["category"] == "very_productive"


def test_buffer_retry_ships_unshipped_records(mocker):
    mocker.patch("time.sleep")
    events = [
        ActivityEvent(time.time(), "main.py - VS Code", "Code",
                      1234, "/home/b/projects/openrescue", None),
        ActivityEvent(time.time(), "Google - Firefox", "Firefox",
                      5678, "/home/b", None),
    ]
    call_count = [0]

    def mock_get_window():
        e = events[call_count[0]]
        call_count[0] += 1
        return e

    mocker.patch("openrescue.main.get_active_window", side_effect=mock_get_window)
    mocker.patch("openrescue.main.get_idle_time", return_value=0.0)

    mock_shipper = MagicMock()
    mock_shipper.push_from_buffer.return_value = True
    mock_metrics = MagicMock()
    mock_metrics.calculate_pulse.return_value = 50.0

    buffered_records = [
        {"id": 1, "app_name": "OldApp", "hostname": "test", "duration": 10.0,
         "timestamp": 1711700000.0, "window_title": "old", "pid": 100,
         "cwd": "/home/b", "project": None, "category": "uncategorized", "shipped": 0},
        {"id": 2, "app_name": "OldApp2", "hostname": "test", "duration": 20.0,
         "timestamp": 1711700001.0, "window_title": "old2", "pid": 101,
         "cwd": "/home/b", "project": None, "category": "productive", "shipped": 0},
    ]
    mock_buffer = MagicMock()
    mock_buffer.get_unshipped.return_value = buffered_records

    config = _make_config()
    tracking_loop(config, mock_shipper, mock_metrics, hostname="test",
                  max_iterations=2, buffer=mock_buffer)

    # Two flushes happen (mid-loop + final), each retries the unshipped records
    assert mock_shipper.push_from_buffer.call_count >= 2
    mock_buffer.mark_shipped.assert_called()


def test_buffer_stops_retry_on_failure(mocker):
    mocker.patch("time.sleep")
    events = [
        ActivityEvent(time.time(), "main.py - VS Code", "Code",
                      1234, "/home/b/projects/openrescue", None),
        ActivityEvent(time.time(), "Google - Firefox", "Firefox",
                      5678, "/home/b", None),
    ]
    call_count = [0]

    def mock_get_window():
        e = events[call_count[0]]
        call_count[0] += 1
        return e

    mocker.patch("openrescue.main.get_active_window", side_effect=mock_get_window)
    mocker.patch("openrescue.main.get_idle_time", return_value=0.0)

    mock_shipper = MagicMock()
    mock_shipper.push_from_buffer.return_value = False
    mock_metrics = MagicMock()
    mock_metrics.calculate_pulse.return_value = 50.0

    buffered_records = [
        {"id": 1, "app_name": "App1", "hostname": "test", "duration": 10.0,
         "timestamp": 1711700000.0, "window_title": "t1", "pid": 100,
         "cwd": "/home/b", "project": None, "category": "uncategorized", "shipped": 0},
        {"id": 2, "app_name": "App2", "hostname": "test", "duration": 20.0,
         "timestamp": 1711700001.0, "window_title": "t2", "pid": 101,
         "cwd": "/home/b", "project": None, "category": "productive", "shipped": 0},
    ]
    mock_buffer = MagicMock()
    mock_buffer.get_unshipped.return_value = buffered_records

    config = _make_config()
    tracking_loop(config, mock_shipper, mock_metrics, hostname="test",
                  max_iterations=2, buffer=mock_buffer)

    # Each flush tries the first record and stops on failure; two flushes happen
    assert mock_shipper.push_from_buffer.call_count >= 1
    mock_buffer.mark_shipped.assert_not_called()
