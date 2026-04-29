from __future__ import annotations

from datetime import datetime

from .models import TuningTaskResult


class SqlTuningAdvisor:
    def __init__(self, connection: object):
        self.connection = connection

    def tune_sql_id(self, sql_id: str, time_limit_seconds: int = 900, drop_after: bool = True) -> TuningTaskResult:
        import oracledb

        task_name = f"STA_{sql_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        cursor = self.connection.cursor()
        cursor.execute(
            """
            begin
              :task_name := dbms_sqltune.create_tuning_task(
                sql_id => :sql_id,
                time_limit => :time_limit,
                task_name => :requested_task_name,
                description => 'SQL tuning agent task for SQL_ID ' || :sql_id
              );
            end;
            """,
            {
                "task_name": cursor.var(str),
                "sql_id": sql_id,
                "time_limit": time_limit_seconds,
                "requested_task_name": task_name,
            },
        )
        cursor.execute("begin dbms_sqltune.execute_tuning_task(task_name => :task_name); end;", {"task_name": task_name})
        report_var = cursor.var(oracledb.DB_TYPE_CLOB)
        cursor.execute(
            """
            begin
              :report := dbms_sqltune.report_tuning_task(
                task_name => :task_name,
                type => 'TEXT',
                level => 'TYPICAL',
                section => 'ALL'
              );
            end;
            """,
            {"report": report_var, "task_name": task_name},
        )
        report = _read_lob(report_var.getvalue())
        if drop_after:
            cursor.execute("begin dbms_sqltune.drop_tuning_task(task_name => :task_name); end;", {"task_name": task_name})
        self.connection.commit()
        return TuningTaskResult(
            sql_id=sql_id,
            task_name=task_name,
            advisor_report=report,
            created_at=datetime.utcnow(),
            metadata={"time_limit_seconds": time_limit_seconds, "dropped_after_completion": drop_after},
        )


def _read_lob(value: object) -> str:
    if value is None:
        return ""
    if hasattr(value, "read"):
        return str(value.read())
    return str(value)
