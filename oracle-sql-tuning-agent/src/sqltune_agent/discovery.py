from __future__ import annotations

from datetime import datetime
from typing import Iterable

from .models import PerformanceBaseline, SqlStatement


class WorkloadDiscovery:
    def __init__(self, connection: object, source: str = "gv$sql"):
        self.connection = connection
        self.source = source.lower()

    def discover(self, max_sql: int, ranking_metric: str) -> list[SqlStatement]:
        if self.source == "awr":
            return self._discover_awr(max_sql, ranking_metric)
        view = "gv$sql" if self.source == "gv$sql" else "v$sql"
        return self._discover_dynamic_view(view, max_sql, ranking_metric)

    def validate_sql_id_exists(self, sql_id: str) -> bool:
        cursor = self.connection.cursor()
        cursor.execute("select count(*) from v$sql where sql_id = :sql_id", {"sql_id": sql_id})
        return int(cursor.fetchone()[0]) > 0

    def capture_baseline(self, sql_id: str) -> PerformanceBaseline | None:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            select sql_id, plan_hash_value, executions,
                   case when executions > 0 then cpu_time / executions else cpu_time end avg_cpu_time,
                   case when executions > 0 then elapsed_time / executions else elapsed_time end avg_elapsed_time,
                   buffer_gets, disk_reads
            from v$sql
            where sql_id = :sql_id
            order by last_active_time desc nulls last
            fetch first 1 rows only
            """,
            {"sql_id": sql_id},
        )
        row = cursor.fetchone()
        if not row:
            return None
        return PerformanceBaseline(
            sql_id=row[0],
            plan_hash_value=row[1],
            executions=int(row[2] or 0),
            avg_cpu_time=float(row[3] or 0),
            avg_elapsed_time=float(row[4] or 0),
            buffer_gets=int(row[5] or 0),
            disk_reads=int(row[6] or 0),
            captured_at=datetime.utcnow(),
        )

    def _discover_dynamic_view(self, view: str, max_sql: int, ranking_metric: str) -> list[SqlStatement]:
        order_by = {
            "avg_cpu_time": "avg_cpu_time desc",
            "avg_elapsed_time": "avg_elapsed_time desc",
            "combined": "(avg_cpu_time + avg_elapsed_time) desc",
        }[ranking_metric]
        inst_col = "inst_id," if view == "gv$sql" else "cast(null as number) inst_id,"
        sql = f"""
            select *
            from (
              select {inst_col}
                     sql_id,
                     plan_hash_value,
                     executions,
                     case when executions > 0 then cpu_time / executions else cpu_time end avg_cpu_time,
                     case when executions > 0 then elapsed_time / executions else elapsed_time end avg_elapsed_time,
                     parsing_schema_name,
                     module,
                     action,
                     buffer_gets,
                     disk_reads,
                     rows_processed,
                     last_active_time,
                     sql_fulltext
              from {view}
              where sql_id is not null
                and command_type not in (47)
                and parsing_schema_name not in ('SYS', 'SYSTEM')
            )
            order by {order_by}
            fetch first :max_sql rows only
        """
        cursor = self.connection.cursor()
        cursor.execute(sql, {"max_sql": max_sql})
        return [_row_to_statement(row) for row in cursor.fetchall()]

    def _discover_awr(self, max_sql: int, ranking_metric: str) -> list[SqlStatement]:
        order_by = {
            "avg_cpu_time": "avg_cpu_time desc",
            "avg_elapsed_time": "avg_elapsed_time desc",
            "combined": "(avg_cpu_time + avg_elapsed_time) desc",
        }[ranking_metric]
        sql = f"""
            select cast(null as number) inst_id,
                   s.sql_id,
                   s.plan_hash_value,
                   s.executions_delta executions,
                   case when s.executions_delta > 0 then s.cpu_time_delta / s.executions_delta else s.cpu_time_delta end avg_cpu_time,
                   case when s.executions_delta > 0 then s.elapsed_time_delta / s.executions_delta else s.elapsed_time_delta end avg_elapsed_time,
                   s.parsing_schema_name,
                   null module,
                   null action,
                   s.buffer_gets_delta buffer_gets,
                   s.disk_reads_delta disk_reads,
                   s.rows_processed_delta rows_processed,
                   cast(null as date) last_active_time,
                   t.sql_text
            from dba_hist_sqlstat s
            join dba_hist_sqltext t on t.sql_id = s.sql_id and t.dbid = s.dbid
            order by {order_by}
            fetch first :max_sql rows only
        """
        cursor = self.connection.cursor()
        cursor.execute(sql, {"max_sql": max_sql})
        return [_row_to_statement(row) for row in cursor.fetchall()]


def _row_to_statement(row: Iterable[object]) -> SqlStatement:
    values = list(row)
    return SqlStatement(
        inst_id=values[0],
        sql_id=values[1],
        plan_hash_value=values[2],
        executions=int(values[3] or 0),
        avg_cpu_time=float(values[4] or 0),
        avg_elapsed_time=float(values[5] or 0),
        parsing_schema_name=values[6],
        module=values[7],
        action=values[8],
        buffer_gets=int(values[9] or 0),
        disk_reads=int(values[10] or 0),
        rows_processed=int(values[11] or 0),
        last_active_time=values[12],
        sql_text=str(values[13] or ""),
    )
