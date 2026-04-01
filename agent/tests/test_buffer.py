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


def test_prune_removes_old_shipped_records(tmp_path):
    db_path = tmp_path / "buffer.db"
    buf = SessionBuffer(db_path)

    # Insert a record with a timestamp 15 days ago
    old_ts = time.time() - (15 * 86400)
    old_id = buf.insert({
        "timestamp": old_ts,
        "app_name": "OldApp",
        "window_title": "old title",
        "pid": 1000,
        "cwd": "/home/b",
        "project": None,
        "hostname": "testhost",
        "duration": 10.0,
        "category": "productive",
    })
    buf.mark_shipped([old_id])

    # Insert a recent shipped record
    recent_id = buf.insert({
        "timestamp": time.time(),
        "app_name": "RecentApp",
        "window_title": "new title",
        "pid": 2000,
        "cwd": "/home/b",
        "project": None,
        "hostname": "testhost",
        "duration": 10.0,
        "category": "productive",
    })
    buf.mark_shipped([recent_id])

    # Insert an old unshipped record (should NOT be pruned)
    buf.insert({
        "timestamp": old_ts,
        "app_name": "OldUnshipped",
        "window_title": "old unshipped",
        "pid": 3000,
        "cwd": "/home/b",
        "project": None,
        "hostname": "testhost",
        "duration": 10.0,
        "category": "productive",
    })

    pruned = buf.prune(max_age_days=10)

    # Only the old shipped record should be removed
    assert pruned == 1

    # Recent shipped record still exists
    cursor = buf._conn.execute("SELECT count(*) FROM sessions WHERE shipped = 1")
    assert cursor.fetchone()[0] == 1

    # Old unshipped record still exists
    unshipped = buf.get_unshipped()
    assert len(unshipped) == 1
    assert unshipped[0]["app_name"] == "OldUnshipped"
