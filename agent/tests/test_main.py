import time
from unittest.mock import MagicMock, patch
from openrescue.main import tracking_loop
from openrescue.config import Config, ServerConfig, TrackingConfig, ProjectsConfig, CategoriesConfig
from openrescue.tracker import ActivityEvent


def test_tracking_loop_single_iteration(mocker):
    config = Config(
        server=ServerConfig(loki_url="http://localhost:3100", mimir_url="http://localhost:9009"),
        tracking=TrackingConfig(poll_interval_seconds=5),
        projects=ProjectsConfig(base_paths=["~/projects"]),
        categories=CategoriesConfig(productive=["code"], neutral=[], distracting=[]),
    )

    mock_event = ActivityEvent(
        timestamp=time.time(),
        window_title="main.py - openrescue - Visual Studio Code",
        app_name="Code",
        pid=1234,
        cwd="/home/b/projects/openrescue",
        project=None,
    )

    mock_get_window = mocker.patch("openrescue.main.get_active_window", return_value=mock_event)
    mock_get_idle = mocker.patch("openrescue.main.get_idle_time", return_value=10.0)
    mock_shipper = MagicMock()
    mock_metrics = MagicMock()

    tracking_loop(config, mock_shipper, mock_metrics, hostname="test", max_iterations=1)

    mock_shipper.push_event.assert_called_once()
    pushed_event = mock_shipper.push_event.call_args[0][0]
    assert pushed_event.project == "openrescue"
    assert pushed_event.idle_seconds == 10.0
    mock_metrics.record_activity.assert_called_once()
