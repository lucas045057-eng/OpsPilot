from __future__ import annotations

import asyncio
import logging
from typing import Any

from .metrics import MetricsStore
from .repair import RepairEngine

logger = logging.getLogger(__name__)


class Monitor:
    def __init__(self, runtime: Any, db: Any, metrics: MetricsStore, settings: Any):
        self.runtime = runtime
        self.db = db
        self.metrics = metrics
        self.settings = settings
        self.repair = RepairEngine(
            runtime,
            db,
            auto_remediate=settings.auto_remediate,
            cooldown=settings.action_cooldown_seconds,
        )
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def run_cycle(self) -> dict[str, Any]:
        actions: list[dict[str, Any]] = []
        for snapshot in self.runtime.list_services():
            data = snapshot.as_dict()
            self.db.upsert_service(data)
            unhealthy = data["status"] != "running" or data.get("health") in {"unhealthy", "dead"}
            if unhealthy:
                result = self.repair.handle_failure(data)
                actions.append({"service": data["name"], **result})
                # Re-read after a successful repair to close the incident in the same cycle.
                if result.get("action_status") == "success":
                    recovered = self.runtime.snapshot(data["name"]).as_dict()
                    self.db.upsert_service(recovered)
                    if recovered["status"] == "running":
                        self.db.recover_alert(data["name"])
            else:
                self.db.recover_alert(data["name"])
        services = self.db.list_services()
        alerts = self.db.list_alerts()
        self.metrics.update(services, alerts)
        return {"services": services, "alerts": alerts, "actions": actions}

    async def loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self.run_cycle()
            except Exception:
                logger.exception("monitor cycle failed")
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=self.settings.monitor_interval_seconds
                )
            except asyncio.TimeoutError:
                pass

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self.loop(), name="opspilot-monitor")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task
            self._task = None

