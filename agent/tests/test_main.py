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
