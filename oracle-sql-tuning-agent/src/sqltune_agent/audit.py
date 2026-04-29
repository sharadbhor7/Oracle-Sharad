from __future__ import annotations

import json

from .models import ImplementationAction, Recommendation, SqlStatement, TuningTaskResult


class AuditRepository:
    def __init__(self, connection: object):
        self.connection = connection

    def record_discovered_sql(self, statements: list[SqlStatement]) -> None:
        cursor = self.connection.cursor()
        for stmt in statements:
            cursor.execute(
                """
                insert into discovered_sql (
                  sql_id, plan_hash_value, executions, avg_cpu_time, avg_elapsed_time,
                  parsing_schema_name, module, action, buffer_gets, disk_reads,
                  rows_processed, last_active_time, sql_text, inst_id
                ) values (
                  :sql_id, :plan_hash_value, :executions, :avg_cpu_time, :avg_elapsed_time,
                  :parsing_schema_name, :module, :action, :buffer_gets, :disk_reads,
                  :rows_processed, :last_active_time, :sql_text, :inst_id
                )
                """,
                stmt.__dict__,
            )
        self.connection.commit()

    def record_tuning_task(self, result: TuningTaskResult) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            insert into tuning_tasks (sql_id, task_name, advisor_report, metadata_json)
            values (:sql_id, :task_name, :advisor_report, :metadata_json)
            """,
            {
                "sql_id": result.sql_id,
                "task_name": result.task_name,
                "advisor_report": result.advisor_report,
                "metadata_json": json.dumps(result.metadata, sort_keys=True),
            },
        )
        self.connection.commit()

    def record_recommendations(self, recommendations: list[Recommendation]) -> None:
        cursor = self.connection.cursor()
        for rec in recommendations:
            cursor.execute(
                """
                insert into recommendations (
                  sql_id, task_name, recommendation_type, summary, findings,
                  recommended_solution, expected_benefit, risk_level,
                  required_privileges, rollback_plan, automated, raw_text, status
                ) values (
                  :sql_id, :task_name, :recommendation_type, :summary, :findings,
                  :recommended_solution, :expected_benefit, :risk_level,
                  :required_privileges, :rollback_plan, :automated, :raw_text, :status
                )
                """,
                {
                    "sql_id": rec.sql_id,
                    "task_name": rec.task_name,
                    "recommendation_type": rec.type.value,
                    "summary": rec.summary,
                    "findings": rec.findings,
                    "recommended_solution": rec.recommended_solution,
                    "expected_benefit": rec.expected_benefit,
                    "risk_level": rec.risk_level.value,
                    "required_privileges": ", ".join(rec.required_privileges),
                    "rollback_plan": rec.rollback_plan,
                    "automated": "Y" if rec.automated else "N",
                    "raw_text": rec.raw_text,
                    "status": rec.status,
                },
            )
        self.connection.commit()

    def record_implementation_action(self, action: ImplementationAction) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            insert into implementation_actions (
              sql_id, recommendation_type, action_name, status, details, rollback_token
            ) values (
              :sql_id, :recommendation_type, :action_name, :status, :details, :rollback_token
            )
            """,
            {
                "sql_id": action.sql_id,
                "recommendation_type": action.recommendation_type.value,
                "action_name": action.action_name,
                "status": action.status,
                "details": action.details,
                "rollback_token": action.rollback_token,
            },
        )
        self.connection.commit()

    def record_rollback_action(
        self,
        sql_id: str,
        rollback_type: str,
        rollback_token: str,
        status: str,
        details: str,
        action_id: int | None = None,
    ) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            insert into rollback_actions (
              sql_id, action_id, rollback_type, rollback_token, status, details
            ) values (
              :sql_id, :action_id, :rollback_type, :rollback_token, :status, :details
            )
            """,
            {
                "sql_id": sql_id,
                "action_id": action_id,
                "rollback_type": rollback_type,
                "rollback_token": rollback_token,
                "status": status,
                "details": details,
            },
        )
        self.connection.commit()

    def fetch_recent_recommendations(self, limit: int = 50) -> list[dict[str, object]]:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            select sql_id, task_name, recommendation_type, risk_level, summary,
                   expected_benefit, automated, status, created_at
            from recommendations
            order by created_at desc
            fetch first :limit rows only
            """,
            {"limit": limit},
        )
        columns = [
            "sql_id",
            "task_name",
            "recommendation_type",
            "risk_level",
            "summary",
            "expected_benefit",
            "automated",
            "status",
            "created_at",
        ]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
