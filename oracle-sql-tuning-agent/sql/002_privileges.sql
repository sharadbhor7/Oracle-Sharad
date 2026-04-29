-- Example privilege grants. Review with your DBA and security team before use.
-- Replace TUNE_AGENT with your agent schema.

grant create session to TUNE_AGENT;
grant advisor to TUNE_AGENT;
grant administer sql management object to TUNE_AGENT;

grant select on sys.v_$sql to TUNE_AGENT;
grant select on sys.gv_$sql to TUNE_AGENT;
grant select on sys.v_$sql_plan to TUNE_AGENT;

-- Optional AWR support. Requires Diagnostics Pack/Tuning Pack licensing.
-- grant select on sys.dba_hist_sqlstat to TUNE_AGENT;
-- grant select on sys.dba_hist_sqltext to TUNE_AGENT;
-- grant select on sys.dba_hist_snapshot to TUNE_AGENT;

-- Medium/high-risk operations should be granted only to human-controlled
-- deployment roles, not to the tuning agent's default runtime schema.
-- Examples:
-- grant analyze any to DBA_APPROVED_TUNING_ROLE;
-- grant create any index to DBA_APPROVED_CHANGE_ROLE;
