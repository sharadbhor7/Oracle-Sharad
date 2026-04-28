import argparse
import json
import os
import re
from decimal import Decimal

import oracledb
from dotenv import load_dotenv
from openai import OpenAI


REALTIME_SQL = """
SELECT *
FROM (
    SELECT
        sql_id,
        parsing_schema_name,
        executions,
        ROUND(cpu_time / 1000000, 2) AS cpu_seconds,
        ROUND(elapsed_time / 1000000, 2) AS elapsed_seconds,
        buffer_gets,
        disk_reads,
        rows_processed,
        ROUND(cpu_time / NULLIF(executions, 0) / 1000000, 4) AS cpu_sec_per_exec,
        SUBSTR(sql_text, 1, 1000) AS sql_text
    FROM v$sql
    WHERE cpu_time > 0
    ORDER BY cpu_time DESC
)
WHERE ROWNUM <= :limit
"""


AWR_SQL = """
SELECT *
FROM (
    SELECT
        s.sql_id,
        MIN(DBMS_LOB.SUBSTR(t.sql_text, 1000, 1)) AS sql_text,
        SUM(s.executions_delta) AS executions,
        ROUND(SUM(s.cpu_time_delta) / 1000000, 2) AS cpu_seconds,
        ROUND(SUM(s.elapsed_time_delta) / 1000000, 2) AS elapsed_seconds,
        SUM(s.buffer_gets_delta) AS buffer_gets,
        SUM(s.disk_reads_delta) AS disk_reads,
        SUM(s.rows_processed_delta) AS rows_processed,
        ROUND(
            SUM(s.cpu_time_delta) / NULLIF(SUM(s.executions_delta), 0) / 1000000,
            4
        ) AS cpu_sec_per_exec
    FROM dba_hist_sqlstat s
    JOIN dba_hist_sqltext t
        ON s.sql_id = t.sql_id
       AND s.dbid = t.dbid
    JOIN dba_hist_snapshot sn
        ON s.snap_id = sn.snap_id
       AND s.dbid = sn.dbid
       AND s.instance_number = sn.instance_number
    WHERE sn.begin_interval_time >= SYSDATE - :days
    GROUP BY s.sql_id
    ORDER BY SUM(s.cpu_time_delta) DESC
)
WHERE ROWNUM <= :limit
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI agent for Oracle top SQL by CPU time."
    )
    parser.add_argument(
        "--mode",
        choices=["realtime", "awr"],
        default="realtime",
        help="Use realtime V$SQL data or historical AWR data.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of SQL statements to analyze.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="AWR lookback window in days. Used only with --mode awr.",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Only print Oracle results as JSON without calling OpenAI.",
    )
    parser.add_argument(
        "--show-full-sql",
        action="store_true",
        help="Send raw SQL text to the model. By default literals are redacted.",
    )
    return parser.parse_args()


def require_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def init_oracle_client():
    client_lib_dir = os.getenv("ORACLE_CLIENT_LIB_DIR")
    if client_lib_dir:
        oracledb.init_oracle_client(lib_dir=client_lib_dir)


def connect_to_oracle():
    init_oracle_client()
    return oracledb.connect(
        user=require_env("ORACLE_USER"),
        password=require_env("ORACLE_PASSWORD"),
        dsn=require_env("ORACLE_DSN"),
    )


def normalize_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "read"):
        return value.read()
    return value


def redact_sql_text(sql_text):
    if not sql_text:
        return sql_text

    redacted = re.sub(r"'([^']|'')*'", "'?'", sql_text)
    redacted = re.sub(r'\b\d+(\.\d+)?\b', "?", redacted)
    return redacted


def fetch_top_sql(connection, mode, limit, days, show_full_sql):
    sql = AWR_SQL if mode == "awr" else REALTIME_SQL
    params = {"limit": limit}
    if mode == "awr":
        params["days"] = days

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [col[0].lower() for col in cursor.description]
        rows = []

        for row in cursor.fetchall():
            item = {
                column: normalize_value(value)
                for column, value in zip(columns, row)
            }
            if not show_full_sql:
                item["sql_text"] = redact_sql_text(item.get("sql_text"))
            rows.append(item)

    return rows


def analyze_with_openai(rows, mode, days):
    model = os.getenv("OPENAI_MODEL", "gpt-4.1")
    client = OpenAI()

    time_window = (
        f"historical AWR data from the last {days} day(s)"
        if mode == "awr"
        else "currently cached V$SQL data"
    )

    prompt = f"""
You are an Oracle database performance tuning assistant.

Analyze the top SQL statements by total CPU time from {time_window}.

Return:
1. Executive summary
2. Top CPU consumers
3. SQL statements with high CPU per execution
4. Likely causes
5. Recommended next checks and tuning actions

Be practical. Mention that V$SQL data can age out of memory when mode is realtime.

Data:
{json.dumps(rows, indent=2)}
"""

    response = client.responses.create(
        model=model,
        input=prompt,
    )
    return response.output_text


def main():
    load_dotenv()
    args = parse_args()

    with connect_to_oracle() as connection:
        rows = fetch_top_sql(
            connection=connection,
            mode=args.mode,
            limit=args.limit,
            days=args.days,
            show_full_sql=args.show_full_sql,
        )

    print(json.dumps(rows, indent=2))

    if args.no_ai:
        return

    print("\nAI Analysis\n")
    print(analyze_with_openai(rows, args.mode, args.days))


if __name__ == "__main__":
    main()
