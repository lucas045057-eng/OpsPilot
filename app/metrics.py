from __future__ import annotations

import os
import time
from typing import Any


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def host_metrics() -> dict[str, float]:
    try:
        import psutil

        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(os.getcwd())
        network = psutil.net_io_counters()
        return {
            "cpu_percent": float(psutil.cpu_percent(interval=None)),
            "memory_percent": float(memory.percent),
            "memory_used_bytes": float(memory.used),
            "memory_total_bytes": float(memory.total),
            "disk_percent": float(disk.percent),
            "network_rx_bytes": float(network.bytes_recv),
            "network_tx_bytes": float(network.bytes_sent),
        }
    except Exception:
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_used_bytes": 0.0,
            "memory_total_bytes": 0.0,
            "disk_percent": 0.0,
            "network_rx_bytes": 0.0,
            "network_tx_bytes": 0.0,
        }


class MetricsStore:
    def __init__(self):
        self.services: dict[str, dict[str, Any]] = {}
        self.alerts: list[dict[str, Any]] = []
        self.host = host_metrics()
        self.updated_at = time.time()

    def update(self, services: list[dict[str, Any]], alerts: list[dict[str, Any]]) -> None:
        self.services = {item["name"]: item for item in services}
        self.alerts = alerts
        self.host = host_metrics()
        self.updated_at = time.time()

    def json(self) -> dict[str, Any]:
        return {
            "updated_at": self.updated_at,
            "host": self.host,
            "services": list(self.services.values()),
            "alerts": self.alerts,
        }

    def prometheus(self) -> str:
        lines = [
            "# HELP opspilot_host_cpu_percent Current host CPU usage percentage.",
            "# TYPE opspilot_host_cpu_percent gauge",
            f"opspilot_host_cpu_percent {self.host['cpu_percent']}",
            "# HELP opspilot_host_memory_percent Current host memory usage percentage.",
            "# TYPE opspilot_host_memory_percent gauge",
            f"opspilot_host_memory_percent {self.host['memory_percent']}",
            "# HELP opspilot_host_disk_percent Current host disk usage percentage.",
            "# TYPE opspilot_host_disk_percent gauge",
            f"opspilot_host_disk_percent {self.host['disk_percent']}",
            "# HELP opspilot_host_network_rx_bytes_total Host received bytes.",
            "# TYPE opspilot_host_network_rx_bytes_total counter",
            f"opspilot_host_network_rx_bytes_total {self.host['network_rx_bytes']}",
            "# HELP opspilot_host_network_tx_bytes_total Host transmitted bytes.",
            "# TYPE opspilot_host_network_tx_bytes_total counter",
            f"opspilot_host_network_tx_bytes_total {self.host['network_tx_bytes']}",
            "# HELP opspilot_service_up Whether a monitored service is running.",
            "# TYPE opspilot_service_up gauge",
            "# HELP opspilot_service_healthy Whether a monitored service reports healthy.",
            "# TYPE opspilot_service_healthy gauge",
        ]
        for service in self.services.values():
            label = _escape(service["name"])
            up = 1 if service["status"] == "running" else 0
            healthy = 1 if service.get("health") in {"healthy", "running"} else 0
            lines.append(f'opspilot_service_up{{service="{label}"}} {up}')
            lines.append(f'opspilot_service_healthy{{service="{label}"}} {healthy}')
        firing = sum(1 for alert in self.alerts if alert["status"] == "firing")
        resolved = sum(1 for alert in self.alerts if alert["status"] == "resolved")
        lines.extend([
            "# HELP opspilot_alerts_firing Number of currently firing alerts.",
            "# TYPE opspilot_alerts_firing gauge",
            f"opspilot_alerts_firing {firing}",
            "# HELP opspilot_alerts_resolved Number of resolved incidents.",
            "# TYPE opspilot_alerts_resolved gauge",
            f"opspilot_alerts_resolved {resolved}",
        ])
        return "\n".join(lines) + "\n"

