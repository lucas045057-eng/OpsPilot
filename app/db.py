from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    """Small SQLite repository; intentionally dependency-free for the demo."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._lock = threading.RLock()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS services (
                    name TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    kind TEXT NOT NULL DEFAULT 'container',
                    runtime_id TEXT,
                    status TEXT NOT NULL DEFAULT 'unknown',
                    health TEXT NOT NULL DEFAULT 'unknown',
                    last_seen TEXT,
                    last_change TEXT,
                    last_error TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alertname TEXT NOT NULL,
                    service TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'firing',
                    message TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    recovered_at TEXT,
                    duration_seconds REAL,
                    action TEXT,
                    action_status TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_alerts_service_status
                    ON alerts(service, status, started_at);
                """
            )

    @staticmethod
    def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row else None

    def upsert_service(self, snapshot: dict[str, Any]) -> None:
        now = utc_now()
        with self._lock, self.connect() as conn:
            old = conn.execute(
                "SELECT status FROM services WHERE name = ?", (snapshot["name"],)
            ).fetchone()
            changed = old is None or old["status"] != snapshot["status"]
            conn.execute(
                """
                INSERT INTO services
                    (name, display_name, kind, runtime_id, status, health,
                     last_seen, last_change, last_error, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    display_name=excluded.display_name,
                    kind=excluded.kind,
                    runtime_id=excluded.runtime_id,
                    status=excluded.status,
                    health=excluded.health,
                    last_seen=excluded.last_seen,
                    last_change=CASE WHEN excluded.last_change IS NOT NULL
                        THEN excluded.last_change ELSE services.last_change END,
                    last_error=excluded.last_error,
                    updated_at=excluded.updated_at
                """,
                (
                    snapshot["name"],
                    snapshot.get("display_name", snapshot["name"]),
                    snapshot.get("kind", "container"),
                    snapshot.get("runtime_id"),
                    snapshot["status"],
                    snapshot.get("health", "unknown"),
                    snapshot.get("checked_at", now),
                    now if changed else None,
                    snapshot.get("message"),
                    now,
                ),
            )

    def list_services(self) -> list[dict[str, Any]]:
        with self._lock, self.connect() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM services ORDER BY name"
            ).fetchall()]

    def get_service(self, name: str) -> dict[str, Any] | None:
        with self._lock, self.connect() as conn:
            return self._dict(conn.execute(
                "SELECT * FROM services WHERE name = ?", (name,)
            ).fetchone())

    def open_alert(self, service: str, message: str, severity: str = "P1") -> dict[str, Any]:
        now = utc_now()
        with self._lock, self.connect() as conn:
            current = conn.execute(
                """
                SELECT * FROM alerts
                WHERE service = ? AND alertname = 'ContainerDown' AND status = 'firing'
                ORDER BY id DESC LIMIT 1
                """,
                (service,),
            ).fetchone()
            if current:
                return dict(current)
            cur = conn.execute(
                """
                INSERT INTO alerts
                    (alertname, service, severity, status, message,
                     started_at, detected_at, created_at)
                VALUES ('ContainerDown', ?, ?, 'firing', ?, ?, ?, ?)
                """,
                (service, severity, message, now, now, now),
            )
            return dict(conn.execute(
                "SELECT * FROM alerts WHERE id = ?", (cur.lastrowid,)
            ).fetchone())

    def set_alert_action(self, alert_id: int, action: str, status: str) -> None:
        with self._lock, self.connect() as conn:
            conn.execute(
                "UPDATE alerts SET action = ?, action_status = ? WHERE id = ?",
                (action, status, alert_id),
            )

    def recover_alert(self, service: str) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        now_text = now.isoformat(timespec="seconds")
        with self._lock, self.connect() as conn:
            current = conn.execute(
                """
                SELECT * FROM alerts
                WHERE service = ? AND alertname = 'ContainerDown' AND status = 'firing'
                ORDER BY id DESC LIMIT 1
                """,
                (service,),
            ).fetchone()
            if not current:
                return None
            try:
                started = datetime.fromisoformat(current["started_at"])
                duration = max(0.0, (now - started).total_seconds())
            except ValueError:
                duration = None
            conn.execute(
                """
                UPDATE alerts
                SET status='resolved', recovered_at=?, duration_seconds=?
                WHERE id=?
                """,
                (now_text, duration, current["id"]),
            )
            return self._dict(conn.execute(
                "SELECT * FROM alerts WHERE id = ?", (current["id"],)
            ).fetchone())

    def list_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock, self.connect() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()]

    def get_alert(self, alert_id: int) -> dict[str, Any] | None:
        with self._lock, self.connect() as conn:
            return self._dict(conn.execute(
                "SELECT * FROM alerts WHERE id = ?", (alert_id,)
            ).fetchone())

