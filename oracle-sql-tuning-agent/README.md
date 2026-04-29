# Oracle SQL Performance Tuning Agent

Production-oriented Oracle 19c+ SQL tuning agent that discovers expensive SQL, runs SQL Tuning Advisor, stores the full advisor output, classifies recommendations by risk, and applies only explicitly allowed low-risk fixes.

The default posture is advisory-only. The agent will not make DDL changes, will not apply HIGH-risk recommendations, and will only accept SQL profiles when policy allows it.

## Capabilities

- Discovers the top SQL statements from `GV$SQL` or `V$SQL` by average CPU time, average elapsed time, or a combined score.
- Captures `SQL_ID`, `PLAN_HASH_VALUE`, executions, parsing schema, module/action, buffer gets, disk reads, rows processed, last active time, and SQL text.
- Optional AWR discovery through `DBA_HIST_SQLSTAT` and `DBA_HIST_SQLTEXT` only when `awr_enabled=true`.
- Runs `DBMS_SQLTUNE.CREATE_TUNING_TASK`, `EXECUTE_TUNING_TASK`, and `REPORT_TUNING_TASK`.
- Parses advisor findings into recommendations with expected benefit, privileges, rollback plan, automation eligibility, and LOW/MEDIUM/HIGH risk.
- Applies only LOW-risk SQL profile acceptance when `advisory_only=false` and either `auto_apply_low_risk=true` or `--approved` is supplied.
- Rolls back accepted SQL profiles with `DBMS_SQLTUNE.DROP_SQL_PROFILE`.
- Stores discovery, advisor reports, recommendations, implementation actions, and rollback actions in audit tables.

## Project Layout

```text
oracle-sql-tuning-agent/
  src/sqltune_agent/
    discovery.py       workload discovery and baselines
    advisor.py         DBMS_SQLTUNE orchestration
    parser.py          advisor report parsing
    risk.py            risk scoring
    policy.py          policy gates
    implementer.py     apply and rollback logic
    audit.py           audit table writes
    cli.py             discover/tune/recommend/apply/rollback/report
  sql/
    001_audit_schema.sql
    002_privileges.sql
    003_dbms_sqltune_wrapper.sql
  tests/
  config.example.yaml
```

## Setup

```bash
cd oracle-sql-tuning-agent
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

On Windows PowerShell:

```powershell
cd oracle-sql-tuning-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Create the audit schema objects:

```sql
@sql/001_audit_schema.sql
```

Review and apply privileges from:

```sql
@sql/002_privileges.sql
```

Optionally install the PL/SQL wrapper:

```sql
@sql/003_dbms_sqltune_wrapper.sql
```

The Python implementation directly calls `DBMS_SQLTUNE`; the wrapper is provided for teams that prefer a narrower PL/SQL API boundary.

## Configuration

Copy `config.example.yaml` and set the password environment variable:

```bash
export ORACLE_TUNE_AGENT_PASSWORD='...'
```

Important defaults:

- `advisory_only: true`
- `auto_apply_low_risk: false`
- `max_sql: 10`
- `ranking_metric: combined`
- `source: gv$sql`
- `awr_enabled: false`
- `drop_tuning_task_after_completion: false`

Keep `drop_tuning_task_after_completion=false` when you plan to accept SQL profiles later using the separate `apply` command. If you run purely advisory reports, you may set it to `true`.

## CLI

Discover expensive SQL and write `discovered_sql` audit rows:

```bash
sqltune-agent --config config.yaml discover
```

Tune the configured top SQL statements:

```bash
sqltune-agent --config config.yaml tune
```

Tune one SQL_ID:

```bash
sqltune-agent --config config.yaml tune --sql-id 9abc123xyz456
```

Run discovery, tuning, parsing, audit storage, and print a recommendation report:

```bash
sqltune-agent --config config.yaml recommend
```

Apply an approved LOW-risk SQL profile recommendation:

```bash
sqltune-agent --config config.yaml apply --sql-id 9abc123xyz456 --task-name STA_9abc123xyz456_20260428120000 --type SQL_PROFILE --approved
```

Rollback an accepted SQL profile:

```bash
sqltune-agent --config config.yaml rollback --sql-id 9abc123xyz456 --profile-name SQLTUNE_9abc123xyz456_20260428120500
```

## Safety Model

LOW risk:

- SQL profile acceptance only.
- Requires `advisory_only=false`.
- Requires `auto_apply_low_risk=true` or `--approved`.
- Audits policy decision, baseline capture, action, and rollback token.

MEDIUM risk:

- SQL plan baselines and optimizer statistics refresh.
- Requires manual approval.
- The current implementation records and reports these recommendations but does not silently execute them.

HIGH risk:

- Index creation, SQL rewrite, partitioning, materialized views, and schema changes.
- Never auto-applied by this agent.
- Requires a reviewed human change process and explicit rollback script.

Additional controls:

- Validates that `SQL_ID` still exists in `V$SQL` before tuning.
- Captures current performance baseline before applying changes.
- Provides rollback for SQL profiles using `DBMS_SQLTUNE.DROP_SQL_PROFILE`.
- Keeps AWR disabled unless the operator explicitly confirms pack licensing through config.

## Licensing Caveat

`V$SQL` and `GV$SQL` discovery are the default sources. AWR discovery and SQL Tuning Advisor usage can involve Oracle Diagnostics Pack and Tuning Pack licensing depending on your Oracle agreement and feature usage. Confirm licensing with your Oracle account team or internal DBA governance before enabling `source: awr`, querying `DBA_HIST_*`, or running advisor workflows in production.

## Required Privileges

Typical runtime privileges:

- `CREATE SESSION`
- `ADVISOR`
- `ADMINISTER SQL MANAGEMENT OBJECT` for SQL profile acceptance
- `SELECT` on `SYS.V_$SQL`, `SYS.GV_$SQL`, and related catalog views

Optional AWR privileges:

- `SELECT` on `SYS.DBA_HIST_SQLSTAT`
- `SELECT` on `SYS.DBA_HIST_SQLTEXT`
- `SELECT` on `SYS.DBA_HIST_SNAPSHOT`

Do not grant broad DDL privileges to the default runtime schema. Use a separate controlled deployment role for approved schema changes.

## Runbook

1. Confirm licensing and maintenance window.
2. Run `discover`.
3. Review top SQL statements in `discovered_sql`.
4. Run `tune` or `recommend`.
5. Review `recommendations`, especially risk level, expected benefit, privileges, and rollback plan.
6. For LOW-risk SQL profiles, decide whether to approve acceptance.
7. Apply with `--approved` or enable `auto_apply_low_risk` under change control.
8. Monitor post-change metrics in `V$SQL`.
9. Roll back with `rollback` if elapsed time, CPU time, or execution behavior degrades beyond your configured threshold.

## Tests

```bash
pytest
```

The tests mock Oracle calls and cover report parsing, risk/policy gates, and discovery SQL construction.
