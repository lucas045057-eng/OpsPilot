# OpsPilot

Docker Service Observability and Automated Self-Healing Platform

OpsPilot is a runnable SRE platform demo that monitors host and service health, records incidents, executes safe allowlisted recovery actions, and exposes Prometheus metrics for Grafana dashboards. It complements AgentOps: AgentOps manages how automation tasks execute; OpsPilot manages how the services behind those tasks are observed, recovered, and reviewed.

## What the demo shows

1. Open `http://localhost:8000` to see service status, CPU/memory/disk metrics, and the incident timeline.
2. Click **Simulate failure** or run `python scripts/fault_injection.py nginx`.
3. The monitor detects the stopped service and creates a P1 incident.
4. The Repair Engine matches the `container_down` runbook and executes the allowlisted `restart` action.
5. The service is checked again, the incident becomes `resolved`, and detection/recovery timestamps plus duration are stored.
6. Open Grafana at `http://localhost:3000`, Prometheus at `http://localhost:9090`, and Alertmanager at `http://localhost:9093` when using Docker mode.

## Architecture

```text
Docker containers / host
          |
          v
  OpsPilot Monitor (FastAPI + Python)
       |             |
       v             v
  SQLite incidents  /metrics
       |             |
       v             v
  Repair Engine   Prometheus -> Grafana
       |
       v
  Docker API (restart / inspect)
```

## Quick start without Docker

This mode works without Docker Desktop and is useful for development and interviews. It keeps the monitoring, alerting, incident, self-healing, and Prometheus metric flow while using a deterministic simulated runtime.

```powershell
cd work/OpsPilot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:RUNTIME_MODE="simulated"
uvicorn app.main:app --reload --port 8000
```

## Docker + Grafana mode

```bash
docker compose up -d --build
```

Services:

| URL | Purpose |
|---|---|
| `http://localhost:8000` | OpsPilot console |
| `http://localhost:3000` | Grafana (`admin` / `opspilot`) |
| `http://localhost:9090` | Prometheus |
| `http://localhost:9093` | Alertmanager |

The Docker runtime reads and restarts `nginx`, `redis`, and `api-service` through the Docker socket. Keep simulated mode if you do not want to grant Docker socket access.

## API surface

```text
GET  /health
GET  /api/services
GET  /api/alerts
GET  /api/stats
GET  /api/metrics
GET  /metrics
POST /api/monitor/tick
POST /api/alerts/webhook
POST /api/services/{name}/stop
POST /api/services/{name}/restart
GET  /api/incidents/{id}/report
```

## Tests and CI

```bash
pytest -q
```

GitHub Actions runs the test suite and builds the Docker image. The tests cover healthy service collection, fault injection, P1 alerting, automated restart and recovery, Prometheus metrics, and manual-review mode.

## Resume-ready keywords

`Python` `FastAPI` `Docker` `Docker Compose` `Prometheus` `Grafana` `Alertmanager` `SQLite` `GitHub Actions` `SRE` `observability` `incident management` `automated remediation` `MTTR`
