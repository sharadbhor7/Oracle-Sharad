from __future__ import annotations

import re

from .models import Recommendation, RecommendationType, RiskLevel, TuningTaskResult
from .risk import RiskScorer


class RecommendationParser:
    def __init__(self, risk_scorer: RiskScorer | None = None):
        self.risk_scorer = risk_scorer or RiskScorer()

    def parse(self, result: TuningTaskResult) -> list[Recommendation]:
        sections = _split_recommendations(result.advisor_report)
        if not sections and result.advisor_report.strip():
            sections = [result.advisor_report]
        recommendations: list[Recommendation] = []
        for section in sections:
            rec_type = self._classify(section)
            risk = self.risk_scorer.score(rec_type, section)
            recommendations.append(
                Recommendation(
                    sql_id=result.sql_id,
                    task_name=result.task_name,
                    type=rec_type,
                    summary=_first_match(section, [r"Recommendation\s*\((.*?)\)", r"Finding\s+\d+:\s*(.*)"]) or "SQL Tuning Advisor recommendation",
                    findings=_extract_block(section, "Finding") or section[:1000],
                    recommended_solution=_extract_block(section, "Recommendation") or _extract_action(section),
                    expected_benefit=_first_match(section, [r"estimated benefit is ([^\n.]+)", r"Benefit:\s*([^\n]+)"]),
                    risk_level=risk,
                    required_privileges=_required_privileges(rec_type),
                    rollback_plan=_rollback_plan(rec_type),
                    automated=(risk == RiskLevel.LOW and rec_type == RecommendationType.SQL_PROFILE),
                    raw_text=section.strip(),
                )
            )
        return recommendations

    def _classify(self, text: str) -> RecommendationType:
        lowered = text.lower()
        if "accept_sql_profile" in lowered or "sql profile" in lowered:
            return RecommendationType.SQL_PROFILE
        if "sql plan baseline" in lowered or "baseline" in lowered:
            return RecommendationType.SQL_PLAN_BASELINE
        if "optimizer statistics" in lowered or "gather_table_stats" in lowered or "stale statistics" in lowered:
            return RecommendationType.STATS_REFRESH
        if "create index" in lowered or "index" in lowered:
            return RecommendationType.INDEX
        if "rewrite" in lowered:
            return RecommendationType.SQL_REWRITE
        if "partition" in lowered:
            return RecommendationType.PARTITIONING
        if "materialized view" in lowered:
            return RecommendationType.MATERIALIZED_VIEW
        if "alter table" in lowered or "schema" in lowered:
            return RecommendationType.SCHEMA_CHANGE
        return RecommendationType.UNKNOWN


def _split_recommendations(report: str) -> list[str]:
    parts = re.split(r"\n-{5,}\n|(?=\nFinding\s+\d+:)", report)
    return [part.strip() for part in parts if "recommend" in part.lower() or "finding" in part.lower()]


def _first_match(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_block(text: str, label: str) -> str | None:
    match = re.search(rf"{label}[^\n]*\n(.*?)(?=\n[A-Z][A-Za-z ]+:\n|\Z)", text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def _extract_action(text: str) -> str:
    match = re.search(r"(execute\s+dbms_sqltune\.accept_sql_profile.*?;)", text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return "Review the SQL Tuning Advisor report and apply the recommended remediation through the approved workflow."


def _required_privileges(rec_type: RecommendationType) -> list[str]:
    common = ["ADVISOR", "SELECT_CATALOG_ROLE or explicit SELECT on V_$SQL/GV_$SQL"]
    if rec_type == RecommendationType.SQL_PROFILE:
        return common + ["ADMINISTER SQL MANAGEMENT OBJECT"]
    if rec_type in {RecommendationType.INDEX, RecommendationType.SCHEMA_CHANGE, RecommendationType.PARTITIONING, RecommendationType.MATERIALIZED_VIEW}:
        return common + ["Object owner privileges or CREATE/ALTER privileges"]
    if rec_type == RecommendationType.STATS_REFRESH:
        return common + ["ANALYZE ANY or object owner privileges for DBMS_STATS"]
    return common


def _rollback_plan(rec_type: RecommendationType) -> str:
    if rec_type == RecommendationType.SQL_PROFILE:
        return "Drop the accepted SQL profile with DBMS_SQLTUNE.DROP_SQL_PROFILE and verify baseline metrics."
    if rec_type == RecommendationType.SQL_PLAN_BASELINE:
        return "Disable or drop the SQL plan baseline with DBMS_SPM after approval."
    if rec_type == RecommendationType.STATS_REFRESH:
        return "Restore saved optimizer statistics with DBMS_STATS.RESTORE_*_STATS where retention permits."
    return "Use a reviewed change script with an explicit backout script; the agent will not automate this change."
