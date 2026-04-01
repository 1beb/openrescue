import time
from pathlib import Path
from openrescue.buffer import SessionBuffer


def test_insert_and_get_unshipped(tmp_path):
    db_path = tmp_path / "buffer.db"
    buf = SessionBuffer(db_path)

    row_id = buf.insert({
        "timestamp": 1711700000.0,
        "app_name": "Code",
        "window_title": "main.py - VS Code",
        "pid": 1234,
        "cwd": "/home/b/projects/openrescue",
        "project": "openrescue",
        "hostname": "testhost",
        "duration": 45.3,
        "category": "very_productive",
    })

    assert row_id == 1
    unshipped = buf.get_unshipped()
    assert len(unshipped) == 1
    assert unshipped[0]["app_name"] == "Code"
    assert unshipped[0]["duration"] == 45.3
    assert unshipped[0]["shipped"] == 0


def test_get_unshipped_respects_limit(tmp_path):
    db_path = tmp_path / "buffer.db"
    buf = SessionBuffer(db_path)

    for i in range(5):
        buf.insert({
            "timestamp": 1711700000.0 + i,
            "app_name": f"App{i}",
            "window_title": "title",
            "pid": 1000 + i,
            "cwd": "/home/b",
            "project": None,
            "hostname": "testhost",
            "duration": 10.0,
            "category": "uncategorized",
        })

    unshipped = buf.get_unshipped(limit=3)
    assert len(unshipped) == 3
    assert unshipped[0]["app_name"] == "App0"
    assert unshipped[2]["app_name"] == "App2"


def test_get_unshipped_returns_empty_when_all_shipped(tmp_path):
    db_path = tmp_path / "buffer.db"
    buf = SessionBuffer(db_path)

    row_id = buf.insert({
        "timestamp": 1711700000.0,
        "app_name": "Code",
        "window_title": "title",
        "pid": 1234,
        "cwd": "/home/b",
        "project": None,
        "hostname": "testhost",
        "duration": 10.0,
        "category": "productive",
    })

    buf.mark_shipped([row_id])
    unshipped = buf.get_unshipped()
    assert len(unshipped) == 0
