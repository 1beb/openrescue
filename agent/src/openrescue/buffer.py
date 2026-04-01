import sqlite3
from pathlib import Path


class SessionBuffer:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_table()

    def _create_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                app_name TEXT NOT NULL,
                window_title TEXT NOT NULL,
                pid INTEGER,
                cwd TEXT,
                project TEXT,
                hostname TEXT NOT NULL,
                duration REAL NOT NULL,
                category TEXT NOT NULL,
                shipped INTEGER NOT NULL DEFAULT 0
            )
        """)
        self._conn.commit()

    def insert(self, data: dict) -> int:
        cursor = self._conn.execute(
            """INSERT INTO sessions
               (timestamp, app_name, window_title, pid, cwd, project, hostname, duration, category)
               VALUES (:timestamp, :app_name, :window_title, :pid, :cwd, :project, :hostname, :duration, :category)""",
            data,
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_unshipped(self, limit: int = 100) -> list[dict]:
        cursor = self._conn.execute(
            "SELECT * FROM sessions WHERE shipped = 0 ORDER BY timestamp ASC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def mark_shipped(self, row_ids: list[int]):
        if not row_ids:
            return
        placeholders = ",".join("?" for _ in row_ids)
        self._conn.execute(
            f"UPDATE sessions SET shipped = 1 WHERE id IN ({placeholders})",
            row_ids,
        )
        self._conn.commit()

    def prune(self, max_age_days: int = 10) -> int:
        import time
        cutoff = time.time() - (max_age_days * 86400)
        cursor = self._conn.execute(
            "DELETE FROM sessions WHERE shipped = 1 AND timestamp < ?",
            (cutoff,),
        )
        self._conn.commit()
        return cursor.rowcount

    def close(self):
        self._conn.close()
