from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.db import Database
from app.metrics import MetricsStore
from app.monitor import Monitor
from app.runtime import SimulatedRuntime


def make_monitor(tmp_path):
    db = Database(tmp_path / "opspilot.db")
    db.init()
    runtime = SimulatedRuntime(("nginx", "redis"))
    settings = SimpleNamespace(
        auto_remediate=True,
        action_cooldown_seconds=0,
        monitor_interval_seconds=1,
    )
    monitor = Monitor(runtime, db, MetricsStore(), settings)
    return db, runtime, monitor


def test_monitor_records_and_recovers_incident(tmp_path):
    db, runtime, monitor = make_monitor(tmp_path)

    first = asyncio.run(monitor.run_cycle())
    assert len(first["services"]) == 2
    assert all(item["status"] == "running" for item in first["services"])

    runtime.stop("nginx")
    second = asyncio.run(monitor.run_cycle())
    assert second["actions"][0]["service"] == "nginx"
    assert second["actions"][0]["action_status"] == "success"
    assert runtime.snapshot("nginx").status == "running"

    alerts = db.list_alerts()
    assert len(alerts) == 1
    assert alerts[0]["status"] == "resolved"
    assert alerts[0]["action"] == "restart"


def test_prometheus_metrics_expose_service_and_host(tmp_path):
    _, runtime, monitor = make_monitor(tmp_path)
    asyncio.run(monitor.run_cycle())
    text = monitor.metrics.prometheus()
    assert 'opspilot_service_up{service="nginx"} 1' in text
    assert "opspilot_host_cpu_percent" in text


def test_manual_mode_keeps_alert_firing(tmp_path):
    db = Database(tmp_path / "manual.db")
    db.init()
    runtime = SimulatedRuntime(("api-service",))
    settings = SimpleNamespace(
        auto_remediate=False,
        action_cooldown_seconds=0,
        monitor_interval_seconds=1,
    )
    monitor = Monitor(runtime, db, MetricsStore(), settings)
    runtime.stop("api-service")
    asyncio.run(monitor.run_cycle())
    alert = db.list_alerts()[0]
    assert alert["status"] == "firing"
    assert alert["action"] == "manual_review"
    assert runtime.snapshot("api-service").status == "stopped"
