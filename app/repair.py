from __future__ import annotations

import time
from typing import Any


class RepairEngine:
    """Whitelist-only repair actions with a cooldown to avoid restart loops."""

    def __init__(self, runtime: Any, db: Any, auto_remediate: bool = True, cooldown: float = 30):
        self.runtime = runtime
        self.db = db
        self.auto_remediate = auto_remediate
        self.cooldown = cooldown
        self.last_action: dict[str, float] = {}

    def handle_failure(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        alert = self.db.open_alert(
            snapshot["name"],
            snapshot.get("message") or "service unavailable",
            severity="P1",
        )
        result = {"alert": alert, "action": None, "action_status": "skipped"}
        if not self.auto_remediate:
            self.db.set_alert_action(alert["id"], "manual_review", "skipped")
            result["action"] = "manual_review"
            return result
        now = time.monotonic()
        previous = self.last_action.get(snapshot["name"], 0)
        if now - previous < self.cooldown:
            result["action"] = "restart"
            result["action_status"] = "cooldown"
            return result
        self.last_action[snapshot["name"]] = now
        try:
            self.runtime.restart(snapshot["name"])
            self.db.set_alert_action(alert["id"], "restart", "success")
            result["action"] = "restart"
            result["action_status"] = "success"
        except Exception as exc:
            self.db.set_alert_action(alert["id"], "restart", f"failed: {exc}")
            result["action"] = "restart"
            result["action_status"] = "failed"
            result["error"] = str(exc)
        return result

