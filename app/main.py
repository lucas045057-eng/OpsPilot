from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import Database
from .metrics import MetricsStore
from .monitor import Monitor
from .runtime import build_runtime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("opspilot")

BASE_DIR = Path(__file__).resolve().parent.parent
db = Database(settings.db_path)
runtime, runtime_name = build_runtime(settings)
metrics = MetricsStore()
monitor = Monitor(runtime, db, metrics, settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    await monitor.run_cycle()
    if settings.enable_background_monitor:
        monitor.start()
    yield
    await monitor.stop()


app = FastAPI(title="OpsPilot", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "runtime": runtime_name, "services": len(db.list_services())}


@app.get("/api/services")
def services():
    return {"data": db.list_services()}


@app.get("/api/alerts")
def alerts(limit: int = 50):
    return {"data": db.list_alerts(max(1, min(limit, 200)))}


@app.post("/api/alerts/webhook")
async def alertmanager_webhook(payload: dict):
    """Persist Alertmanager notifications so the incident timeline has one source of truth."""
    accepted = 0
    for item in payload.get("alerts", []):
        labels = item.get("labels") or {}
        annotations = item.get("annotations") or {}
        service = labels.get("service")
        if not service or service not in settings.monitored_services:
            continue
        severity = labels.get("severity", labels.get("level", "P1"))
        if severity.lower() == "critical":
            severity = "P1"
        message = annotations.get("description") or annotations.get("summary") or "Alertmanager notification"
        if item.get("status") == "resolved":
            db.recover_alert(service)
        else:
            db.open_alert(service, message, severity=severity)
        accepted += 1
    return {"accepted": True, "received": len(payload.get("alerts", [])), "persisted": accepted}


@app.get("/api/stats")
def stats():
    services = db.list_services()
    alert_data = db.list_alerts(200)
    return {
        "runtime": runtime_name,
        "services_total": len(services),
        "services_up": sum(1 for item in services if item["status"] == "running"),
        "alerts_firing": sum(1 for item in alert_data if item["status"] == "firing"),
        "incidents_total": len(alert_data),
        "incidents_resolved": sum(1 for item in alert_data if item["status"] == "resolved"),
    }


@app.get("/api/metrics")
def metrics_json():
    return metrics.json()


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    return metrics.prometheus()


@app.post("/api/monitor/tick")
async def monitor_tick():
    return await monitor.run_cycle()


def _require_service(name: str) -> None:
    if name not in settings.monitored_services:
        raise HTTPException(status_code=404, detail=f"Unknown service: {name}")


@app.post("/api/services/{name}/stop")
def stop_service(name: str):
    _require_service(name)
    try:
        snapshot = runtime.stop(name)
        return {"message": "service stopped", "data": snapshot.as_dict()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/services/{name}/restart")
def restart_service(name: str):
    _require_service(name)
    try:
        snapshot = runtime.restart(name)
        return {"message": "service restarted", "data": snapshot.as_dict()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/incidents/{incident_id}/report")
def incident_report(incident_id: int):
    incident = db.get_alert(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    duration = incident.get("duration_seconds")
    duration_text = f"{duration:.1f}s" if isinstance(duration, (int, float)) else "ongoing"
    return {
        "incident": incident,
        "report": (
            "Incident Report\n"
            "====================\n"
            f"事件: {incident['service']} service unavailable\n"
            f"等级: {incident['severity']}\n"
            f"发生时间: {incident['started_at']}\n"
            f"检测时间: {incident['detected_at']}\n"
            f"恢复时间: {incident.get('recovered_at') or 'ongoing'}\n"
            f"故障持续: {duration_text}\n"
            f"MTTR: {duration_text}\n"
            f"原因: {incident['message']}\n"
            f"处理: {incident.get('action') or 'manual review'}\n"
            f"状态: {incident['status']}\n"
        ),
    }
