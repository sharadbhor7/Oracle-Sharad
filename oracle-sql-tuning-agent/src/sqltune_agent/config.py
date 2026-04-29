from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class DatabaseConfig:
    user: str
    password: str
    dsn: str
    mode: str = "thin"


@dataclass(frozen=True)
class RollbackThreshold:
    elapsed_time_pct: float = 20
    cpu_time_pct: float = 20
    min_executions: int = 10


@dataclass(frozen=True)
class AgentConfig:
    advisory_only: bool = True
    auto_apply_low_risk: bool = False
    max_sql: int = 10
    ranking_metric: str = "combined"
    source: str = "gv$sql"
    awr_enabled: bool = False
    drop_tuning_task_after_completion: bool = True
    execution_window: dict[str, str] | None = None
    rollback_threshold: RollbackThreshold = RollbackThreshold()


@dataclass(frozen=True)
class NotificationConfig:
    enabled: bool = False
    webhook_url: str | None = None
    email_to: list[str] | None = None


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    file: str | None = "sqltune-agent.log"


@dataclass(frozen=True)
class AppConfig:
    database: DatabaseConfig
    agent: AgentConfig
    notifications: NotificationConfig
    logging: LoggingConfig


def load_config(path: str | Path) -> AppConfig:
    data = _read_yaml(path)
    database = data.get("database", {})
    password = os.getenv(database.get("password_env", ""), database.get("password", ""))
    if not password:
        raise ValueError("Database password missing. Set database.password_env or database.password.")

    agent_data = data.get("agent", {})
    threshold = RollbackThreshold(**agent_data.get("rollback_threshold", {}))
    agent = AgentConfig(
        advisory_only=agent_data.get("advisory_only", True),
        auto_apply_low_risk=agent_data.get("auto_apply_low_risk", False),
        max_sql=int(agent_data.get("max_sql", 10)),
        ranking_metric=agent_data.get("ranking_metric", "combined"),
        source=agent_data.get("source", "gv$sql").lower(),
        awr_enabled=agent_data.get("awr_enabled", False),
        drop_tuning_task_after_completion=agent_data.get("drop_tuning_task_after_completion", True),
        execution_window=agent_data.get("execution_window"),
        rollback_threshold=threshold,
    )
    if agent.ranking_metric not in {"avg_cpu_time", "avg_elapsed_time", "combined"}:
        raise ValueError("ranking_metric must be avg_cpu_time, avg_elapsed_time, or combined")
    if agent.source == "awr" and not agent.awr_enabled:
        raise ValueError("AWR source requires awr_enabled=true after licensing confirmation")

    notifications = data.get("notifications", {})
    webhook_url = os.getenv(notifications.get("webhook_url_env", ""), None)
    return AppConfig(
        database=DatabaseConfig(
            user=database["user"],
            password=password,
            dsn=database["dsn"],
            mode=database.get("mode", "thin"),
        ),
        agent=agent,
        notifications=NotificationConfig(
            enabled=notifications.get("enabled", False),
            webhook_url=webhook_url,
            email_to=notifications.get("email_to", []),
        ),
        logging=LoggingConfig(**data.get("logging", {})),
    )


def _read_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
