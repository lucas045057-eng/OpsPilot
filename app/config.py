from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "OpsPilot"
    database_path: str = os.getenv("DATABASE_PATH", "data/opspilot.db")
    runtime_mode: str = os.getenv("RUNTIME_MODE", "auto")
    monitor_interval_seconds: float = float(os.getenv("MONITOR_INTERVAL_SECONDS", "5"))
    auto_remediate: bool = _bool("AUTO_REMEDIATE", True)
    action_cooldown_seconds: float = float(os.getenv("ACTION_COOLDOWN_SECONDS", "30"))
    enable_background_monitor: bool = _bool("ENABLE_BACKGROUND_MONITOR", True)
    monitored_services: tuple[str, ...] = tuple(
        item.strip()
        for item in os.getenv("MONITORED_SERVICES", "nginx,redis,api-service").split(",")
        if item.strip()
    )

    @property
    def db_path(self) -> Path:
        path = Path(self.database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()

