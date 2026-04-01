import json
import requests
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


def test_push_from_buffer_sends_to_loki(mocker):
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 204

    shipper = LokiShipper("http://localhost:3100")
    record = {
        "id": 1,
        "timestamp": 1711700000.0,
        "app_name": "Code",
        "window_title": "main.py - VS Code",
        "pid": 1234,
        "cwd": "/home/b/projects/openrescue",
        "project": "openrescue",
        "hostname": "testhost",
        "duration": 45.3,
        "category": "very_productive",
        "shipped": 0,
    }

    result = shipper.push_from_buffer(record)

    assert result is True
    mock_post.assert_called_once()
    payload = mock_post.call_args[1]["json"]
    stream = payload["streams"][0]
    assert stream["stream"]["app"] == "Code"
    assert stream["stream"]["hostname"] == "testhost"
    assert stream["stream"]["project"] == "openrescue"

    log_data = json.loads(stream["values"][0][1])
    assert log_data["duration_seconds"] == 45.3


def test_push_from_buffer_returns_false_on_failure(mocker):
    mock_post = mocker.patch("requests.post")
    mock_post.side_effect = requests.RequestException("connection refused")

    shipper = LokiShipper("http://localhost:3100")
    record = {
        "id": 1,
        "timestamp": 1711700000.0,
        "app_name": "Code",
        "window_title": "main.py",
        "pid": 1234,
        "cwd": "/home/b",
        "project": None,
        "hostname": "testhost",
        "duration": 10.0,
        "category": "productive",
        "shipped": 0,
    }

    result = shipper.push_from_buffer(record)

    assert result is False


def test_push_from_buffer_omits_none_project(mocker):
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 204

    shipper = LokiShipper("http://localhost:3100")
    record = {
        "id": 1,
        "timestamp": 1711700000.0,
        "app_name": "Firefox",
        "window_title": "Google",
        "pid": 5678,
        "cwd": "/home/b",
        "project": None,
        "hostname": "testhost",
        "duration": 10.0,
        "category": "uncategorized",
        "shipped": 0,
    }

    shipper.push_from_buffer(record)

    payload = mock_post.call_args[1]["json"]
    stream = payload["streams"][0]
    assert "project" not in stream["stream"]
