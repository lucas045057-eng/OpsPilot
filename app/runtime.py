from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class ServiceSnapshot:
    name: str
    display_name: str
    status: str
    health: str
    message: str = ""
    runtime_id: str | None = None
    kind: str = "container"
    checked_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "status": self.status,
            "health": self.health,
            "message": self.message,
            "runtime_id": self.runtime_id,
            "kind": self.kind,
            "checked_at": self.checked_at or now_iso(),
        }


class SimulatedRuntime:
    """A deterministic local runtime so the demo works without Docker Desktop."""

    def __init__(self, services: tuple[str, ...]):
        self.states = {name: "running" for name in services}
        self.health = {name: "healthy" for name in services}

    def list_services(self) -> list[ServiceSnapshot]:
        return [self.snapshot(name) for name in self.states]

    def snapshot(self, name: str) -> ServiceSnapshot:
        if name not in self.states:
            raise KeyError(name)
        status = self.states[name]
        return ServiceSnapshot(
            name=name,
            display_name=name,
            status=status,
            health=self.health[name],
            message="" if status == "running" else "simulated container stopped",
            runtime_id=f"sim-{name}",
            checked_at=now_iso(),
        )

    def stop(self, name: str) -> ServiceSnapshot:
        if name not in self.states:
            raise KeyError(name)
        self.states[name] = "stopped"
        self.health[name] = "unhealthy"
        return self.snapshot(name)

    def start(self, name: str) -> ServiceSnapshot:
        if name not in self.states:
            raise KeyError(name)
        self.states[name] = "running"
        self.health[name] = "healthy"
        return self.snapshot(name)

    def restart(self, name: str) -> ServiceSnapshot:
        return self.start(name)


class DockerRuntime:
    def __init__(self, services: tuple[str, ...]):
        import docker

        self.client = docker.from_env()
        self.services = services

    def list_services(self) -> list[ServiceSnapshot]:
        return [self.snapshot(name) for name in self.services]

    def snapshot(self, name: str) -> ServiceSnapshot:
        try:
            container = self.client.containers.get(name)
        except Exception as exc:
            # A missing container is an observable outage, not a reason to stop
            # the monitor itself during a rolling deploy or compose startup.
            return ServiceSnapshot(
                name=name,
                display_name=name,
                status="stopped",
                health="unhealthy",
                message=f"docker container unavailable: {exc}",
                runtime_id=None,
                checked_at=now_iso(),
            )
        status = container.status
        attrs = container.attrs.get("State", {})
        health_info = attrs.get("Health", {}) or {}
        health = health_info.get("Status", "healthy" if status == "running" else "unhealthy")
        return ServiceSnapshot(
            name=name,
            display_name=name,
            status="running" if status == "running" else "stopped",
            health=health,
            message="" if status == "running" else f"docker status: {status}",
            runtime_id=container.id[:12],
            checked_at=now_iso(),
        )

    def stop(self, name: str) -> ServiceSnapshot:
        container = self.client.containers.get(name)
        container.stop()
        return self.snapshot(name)

    def start(self, name: str) -> ServiceSnapshot:
        container = self.client.containers.get(name)
        container.start()
        return self.snapshot(name)

    def restart(self, name: str) -> ServiceSnapshot:
        container = self.client.containers.get(name)
        container.restart()
        return self.snapshot(name)


def build_runtime(settings: Any) -> tuple[Any, str]:
    mode = settings.runtime_mode.lower()
    if mode != "simulated":
        try:
            runtime = DockerRuntime(settings.monitored_services)
            runtime.client.ping()
            return runtime, "docker"
        except Exception as exc:
            logger.info("Docker runtime unavailable, using simulation: %s", exc)
            if mode == "docker":
                raise
    return SimulatedRuntime(settings.monitored_services), "simulated"
