-- Audit schema for Oracle SQL Performance Tuning Agent.
-- Run as the application schema owner, for example TUNE_AGENT.

create table discovered_sql (
  id number generated always as identity primary key,
  discovered_at timestamp default systimestamp not null,
  sql_id varchar2(13) not null,
  plan_hash_value number,
  executions number,
  avg_cpu_time number,
  avg_elapsed_time number,
  parsing_schema_name varchar2(128),
  module varchar2(64),
  action varchar2(64),
  buffer_gets number,
  disk_reads number,
  rows_processed number,
  last_active_time date,
  sql_text clob,
  inst_id number
);

create index discovered_sql_ix1 on discovered_sql (discovered_at, sql_id);

create table tuning_tasks (
  id number generated always as identity primary key,
  created_at timestamp default systimestamp not null,
  sql_id varchar2(13) not null,
  task_name varchar2(128) not null,
  advisor_report clob not null,
  metadata_json clob,
  status varchar2(30) default 'COMPLETED' not null
);

create unique index tuning_tasks_uq1 on tuning_tasks (task_name);
create index tuning_tasks_ix1 on tuning_tasks (sql_id, created_at);

create table recommendations (
  id number generated always as identity primary key,
  created_at timestamp default systimestamp not null,
  sql_id varchar2(13) not null,
  task_name varchar2(128) not null,
  recommendation_type varchar2(40) not null,
  summary varchar2(4000),
  findings clob,
  recommended_solution clob,
  expected_benefit varchar2(1000),
  risk_level varchar2(10) check (risk_level in ('LOW', 'MEDIUM', 'HIGH')),
  required_privileges varchar2(4000),
  rollback_plan clob,
  automated char(1) check (automated in ('Y', 'N')),
  raw_text clob,
  status varchar2(30) default 'PENDING' not null
);

create index recommendations_ix1 on recommendations (sql_id, risk_level, status);

create table implementation_actions (
  id number generated always as identity primary key,
  action_at timestamp default systimestamp not null,
  sql_id varchar2(13) not null,
  recommendation_type varchar2(40) not null,
  action_name varchar2(80) not null,
  status varchar2(30) not null,
  details clob,
  rollback_token varchar2(256),
  operator_name varchar2(128) default sys_context('USERENV', 'SESSION_USER')
);

create index implementation_actions_ix1 on implementation_actions (sql_id, action_at);

create table rollback_actions (
  id number generated always as identity primary key,
  rollback_at timestamp default systimestamp not null,
  sql_id varchar2(13) not null,
  action_id number,
  rollback_type varchar2(40) not null,
  rollback_token varchar2(256),
  status varchar2(30) not null,
  details clob,
  constraint rollback_actions_fk1 foreign key (action_id) references implementation_actions(id)
);

create index rollback_actions_ix1 on rollback_actions (sql_id, rollback_at);
