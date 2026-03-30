import os
from unittest.mock import patch, MagicMock
from openrescue.tracker import get_active_window_x11, get_project_from_cwd, ActivityEvent


def test_get_active_window_x11(mocker):
    mocker.patch(
        "openrescue.tracker._run_cmd",
        side_effect=lambda cmd: {
            "xdotool getactivewindow": "12345",
            "xdotool getactivewindow getwindowname": "main.py - openrescue - Visual Studio Code",
            "xdotool getactivewindow getwindowpid": "9876",
            "xprop -id 12345 WM_CLASS": 'WM_CLASS(STRING) = "code", "Code"',
        }[" ".join(cmd)],
    )
    mocker.patch("os.readlink", return_value="/home/b/projects/openrescue")

    event = get_active_window_x11()

    assert event.window_title == "main.py - openrescue - Visual Studio Code"
    assert event.app_name == "Code"
    assert event.pid == 9876
    assert event.cwd == "/home/b/projects/openrescue"


def test_get_project_from_cwd():
    assert get_project_from_cwd("/home/b/projects/openrescue", ["~/projects"]) == "openrescue"
    assert get_project_from_cwd("/home/b/projects/openrescue/src", ["~/projects"]) == "openrescue"
    assert get_project_from_cwd("/usr/bin", ["~/projects"]) is None
    assert get_project_from_cwd(None, ["~/projects"]) is None


def test_get_project_from_title():
    from openrescue.tracker import get_project_from_title

    assert get_project_from_title("main.py - openrescue - Visual Studio Code") == "openrescue"
    assert get_project_from_title("~/projects/myapp: bash") == "myapp"
    assert get_project_from_title("Google - Firefox") is None
