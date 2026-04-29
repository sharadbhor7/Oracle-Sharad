from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RecommendationType(str, Enum):
    SQL_PROFILE = "SQL_PROFILE"
    SQL_PLAN_BASELINE = "SQL_PLAN_BASELINE"
    STATS_REFRESH = "STATS_REFRESH"
    INDEX = "INDEX"
    SQL_REWRITE = "SQL_REWRITE"
    PARTITIONING = "PARTITIONING"
    MATERIALIZED_VIEW = "MATERIALIZED_VIEW"
    SCHEMA_CHANGE = "SCHEMA_CHANGE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SqlStatement:
    sql_id: str
    plan_hash_value: int | None
    parsing_schema_name: str | None
    module: str | None
    action: str | None
    executions: int
    avg_cpu_time: float
    avg_elapsed_time: float
    buffer_gets: int
    disk_reads: int
    rows_processed: int
    last_active_time: datetime | None
    sql_text: str
    inst_id: int | None = None


@dataclass(frozen=True)
class PerformanceBaseline:
    sql_id: str
    plan_hash_value: int | None
    executions: int
    avg_cpu_time: float
    avg_elapsed_time: float
    buffer_gets: int
    disk_reads: int
    captured_at: datetime


@dataclass
class TuningTaskResult:
    sql_id: str
    task_name: str
    advisor_report: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Recommendation:
    sql_id: str
    task_name: str
    type: RecommendationType
    summary: str
    findings: str
    recommended_solution: str
    expected_benefit: str | None
    risk_level: RiskLevel
    required_privileges: list[str]
    rollback_plan: str
    automated: bool
    raw_text: str
    status: str = "PENDING"


@dataclass
class ImplementationAction:
    sql_id: str
    recommendation_type: RecommendationType
    action_name: str
    status: str
    details: str
    rollback_token: str | None = None
