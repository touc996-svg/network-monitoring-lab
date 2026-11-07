from __future__ import annotations

import socket
import time
from datetime import datetime, timezone
from typing import Any

from .database import connect
from .schemas import TargetCreate


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_target(data: TargetCreate) -> dict[str, Any]:
    with connect() as db:
        cursor = db.execute(
            """INSERT INTO targets(name, host, check_type, port, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (data.name, data.host, data.check_type, data.port, utc_now()),
        )
        row = db.execute(
            "SELECT * FROM targets WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    result = dict(row)
    result["enabled"] = bool(result["enabled"])
    return result


def get_target(target_id: int) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM targets WHERE id = ?", (target_id,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["enabled"] = bool(result["enabled"])
    return result


def list_targets() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT * FROM targets ORDER BY name").fetchall()
    results = [dict(row) for row in rows]
    for item in results:
        item["enabled"] = bool(item["enabled"])
    return results


def run_check(target_id: int) -> dict[str, Any] | None:
    target = get_target(target_id)
    if target is None:
        return None

    started = time.perf_counter()
    try:
        if target["check_type"] == "tcp":
            connection = socket.create_connection(
                (target["host"], target["port"]), timeout=2.0
            )
            connection.close()
            message = f"TCP port {target['port']} is reachable."
        else:
            records = socket.getaddrinfo(
                target["host"], None, type=socket.SOCK_STREAM
            )
            addresses = sorted({record[4][0] for record in records})
            if not addresses:
                raise OSError("No DNS addresses returned.")
            message = "DNS resolved: " + ", ".join(addresses[:3])

        status = "up"
    except (OSError, ValueError) as exc:
        status = "down"
        message = f"{type(exc).__name__}: {str(exc)[:220]}"

    latency = round((time.perf_counter() - started) * 1000, 2)
    checked_at = utc_now()

    with connect() as db:
        cursor = db.execute(
            """INSERT INTO checks(target_id, status, latency_ms, message, checked_at)
               VALUES (?, ?, ?, ?, ?)""",
            (target_id, status, latency, message, checked_at),
        )
        row = db.execute(
            "SELECT * FROM checks WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()

    return {"target": target, "check": dict(row)}


def recent_checks(limit: int = 25) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute(
            """SELECT c.id, c.target_id, t.name AS target_name, t.host,
                      t.check_type, t.port, c.status, c.latency_ms,
                      c.message, c.checked_at
               FROM checks c JOIN targets t ON t.id = c.target_id
               ORDER BY c.id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def monitoring_summary() -> dict[str, int]:
    with connect() as db:
        total = db.execute("SELECT COUNT(*) FROM targets WHERE enabled = 1").fetchone()[0]
        up = db.execute("""
            SELECT COUNT(*) FROM checks
            WHERE id IN (SELECT MAX(id) FROM checks GROUP BY target_id)
              AND status = 'up'
        """).fetchone()[0]
        down = db.execute("""
            SELECT COUNT(*) FROM checks
            WHERE id IN (SELECT MAX(id) FROM checks GROUP BY target_id)
              AND status = 'down'
        """).fetchone()[0]
    return {
        "total_targets": total,
        "up_targets": up,
        "down_targets": down,
        "unchecked_targets": max(total - up - down, 0),
    }
