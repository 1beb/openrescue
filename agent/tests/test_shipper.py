import json
from openrescue.shipper import LokiShipper
from openrescue.tracker import ActivityEvent


def test_push_session_formats_correctly(mocker):
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 204

    shipper = LokiShipper("http://localhost:3100")
    event = ActivityEvent(
        timestamp=1711700000.0,
        window_title="main.py - openrescue - VS Code",
        app_name="Code",
        pid=1234,
        cwd="/home/b/projects/openrescue",
        project="openrescue",
    )
    shipper.push_session(event, hostname="testhost", duration=45.3)

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[0][0] == "http://localhost:3100/loki/api/v1/push"

    payload = call_args[1]["json"]
    stream = payload["streams"][0]
    assert stream["stream"]["app"] == "Code"
    assert stream["stream"]["project"] == "openrescue"
    assert stream["stream"]["hostname"] == "testhost"

    log_data = json.loads(stream["values"][0][1])
    assert log_data["duration_seconds"] == 45.3


def test_push_session_omits_none_project(mocker):
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 204

    shipper = LokiShipper("http://localhost:3100")
    event = ActivityEvent(
        timestamp=1711700000.0,
        window_title="Google - Firefox",
        app_name="Firefox",
        pid=1234,
        cwd="/home/b",
        project=None,
    )
    shipper.push_session(event, hostname="testhost", duration=10.0)

    payload = mock_post.call_args[1]["json"]
    stream = payload["streams"][0]
    assert "project" not in stream["stream"]
