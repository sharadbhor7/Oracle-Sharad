# Oracle AI SQL CPU Agent

This Python CLI connects to an Oracle database, gets the top SQL statements by CPU time, and optionally asks OpenAI to summarize likely tuning actions.

## Files

- `sql_agent.py` - main CLI agent
- `.env.example` - required environment variables
- `requirements.txt` - Python dependencies

## Setup

```powershell
cd oracle-ai-sql-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

```text
ORACLE_USER=monitor_user
ORACLE_PASSWORD=your_password
ORACLE_DSN=host:1521/service_name
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1
```

## Run Realtime Analysis

Realtime mode uses `V$SQL`, which shows SQL currently available in the shared pool.

```powershell
python sql_agent.py --mode realtime
```

Only print the top 20 SQL data without AI analysis:

```powershell
python sql_agent.py --mode realtime --no-ai
```

## Run Historical AWR Analysis

AWR mode uses `DBA_HIST_SQLSTAT`, `DBA_HIST_SQLTEXT`, and `DBA_HIST_SNAPSHOT`.

```powershell
python sql_agent.py --mode awr --days 1
```

## Required Oracle Grants

For realtime mode:

```sql
GRANT SELECT ON v_$sql TO monitor_user;
```

For AWR mode:

```sql
GRANT SELECT ON dba_hist_sqlstat TO monitor_user;
GRANT SELECT ON dba_hist_sqltext TO monitor_user;
GRANT SELECT ON dba_hist_snapshot TO monitor_user;
```

Some environments use a broader role:

```sql
GRANT SELECT_CATALOG_ROLE TO monitor_user;
```

Use the narrow grants when possible.

## Notes

- Oracle CPU time is stored in microseconds, so the agent converts it to seconds.
- By default, quoted literals and numbers inside SQL text are redacted before sending data to OpenAI.
- Use `--show-full-sql` only if your security policy allows sending raw SQL text to the model.
- AWR usage may require the appropriate Oracle Diagnostics Pack license.
