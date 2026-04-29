create or replace package sqltune_agent_pkg authid definer as
  function create_task_for_sql_id(
    p_sql_id in varchar2,
    p_task_name in varchar2,
    p_time_limit in number default 900
  ) return varchar2;

  procedure execute_task(p_task_name in varchar2);

  function report_task(p_task_name in varchar2) return clob;

  procedure drop_task(p_task_name in varchar2);

  function accept_profile(
    p_task_name in varchar2,
    p_profile_name in varchar2,
    p_force_match in boolean default false
  ) return varchar2;

  procedure drop_profile(p_profile_name in varchar2);
end sqltune_agent_pkg;
/

create or replace package body sqltune_agent_pkg as
  function create_task_for_sql_id(
    p_sql_id in varchar2,
    p_task_name in varchar2,
    p_time_limit in number default 900
  ) return varchar2 is
    l_task_name varchar2(128);
  begin
    l_task_name := dbms_sqltune.create_tuning_task(
      sql_id => p_sql_id,
      time_limit => p_time_limit,
      task_name => p_task_name,
      description => 'SQL tuning agent task for SQL_ID ' || p_sql_id
    );
    return l_task_name;
  end;

  procedure execute_task(p_task_name in varchar2) is
  begin
    dbms_sqltune.execute_tuning_task(task_name => p_task_name);
  end;

  function report_task(p_task_name in varchar2) return clob is
  begin
    return dbms_sqltune.report_tuning_task(
      task_name => p_task_name,
      type => 'TEXT',
      level => 'TYPICAL',
      section => 'ALL'
    );
  end;

  procedure drop_task(p_task_name in varchar2) is
  begin
    dbms_sqltune.drop_tuning_task(task_name => p_task_name);
  exception
    when others then
      if sqlcode != -13605 then
        raise;
      end if;
  end;

  function accept_profile(
    p_task_name in varchar2,
    p_profile_name in varchar2,
    p_force_match in boolean default false
  ) return varchar2 is
  begin
    dbms_sqltune.accept_sql_profile(
      task_name => p_task_name,
      name => p_profile_name,
      replace => false,
      force_match => p_force_match
    );
    return p_profile_name;
  end;

  procedure drop_profile(p_profile_name in varchar2) is
  begin
    dbms_sqltune.drop_sql_profile(name => p_profile_name, ignore => true);
  end;
end sqltune_agent_pkg;
/
