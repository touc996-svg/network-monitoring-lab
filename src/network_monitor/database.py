from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def database_path() -> Path:
    path = Path(os.getenv("NETWORK_MONITOR_DB_PATH", "data/network_monitor.db")).expanduser()
    return path if path.is_absolute() else Path.cwd() / path


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 10000")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize_database() -> None:
    with connect() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                host TEXT NOT NULL,
                check_type TEXT NOT NULL CHECK(check_type IN ('tcp','dns')),
                port INTEGER,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                CHECK((check_type = 'tcp' AND port BETWEEN 1 AND 65535)
                   OR (check_type = 'dns' AND port IS NULL)),
                UNIQUE(host, check_type, port)
            );

            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
                status TEXT NOT NULL CHECK(status IN ('up','down')),
                latency_ms REAL,
                message TEXT NOT NULL,
                checked_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_checks_target_time
                ON checks(target_id, checked_at DESC);
        """)
