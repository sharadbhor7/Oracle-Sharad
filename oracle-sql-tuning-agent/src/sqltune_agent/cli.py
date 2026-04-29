from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .advisor import SqlTuningAdvisor
from .audit import AuditRepository
from .config import load_config
from .db import OracleDatabase
from .discovery import WorkloadDiscovery
from .implementer import RecommendationImplementer
from .logging_config import configure_logging
from .parser import RecommendationParser
from .policy import PolicyGate
from .report import render_recommendations

LOGGER = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sqltune-agent")
    parser.add_argument("--config", default="config.example.yaml", help="Path to YAML config")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("discover")
    tune = sub.add_parser("tune")
    tune.add_argument("--sql-id")
    sub.add_parser("recommend")
    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("--sql-id", required=True)
    apply_parser.add_argument("--task-name", required=True)
    apply_parser.add_argument("--type", default="SQL_PROFILE")
    apply_parser.add_argument("--approved", action="store_true")
    rollback = sub.add_parser("rollback")
    rollback.add_argument("--sql-id", required=True)
    rollback.add_argument("--profile-name", required=True)
    sub.add_parser("report")
    args = parser.parse_args(argv)

    config = load_config(Path(args.config))
    configure_logging(config.logging)
    database = OracleDatabase(config.database)
    with database.connect() as connection:
        discovery = WorkloadDiscovery(connection, source=config.agent.source)
        audit = AuditRepository(connection)
        if args.command == "discover":
            statements = discovery.discover(config.agent.max_sql, config.agent.ranking_metric)
            audit.record_discovered_sql(statements)
            for stmt in statements:
                print(f"{stmt.sql_id} plan={stmt.plan_hash_value} avg_cpu={stmt.avg_cpu_time:.2f} avg_elapsed={stmt.avg_elapsed_time:.2f}")
            return 0

        if args.command == "tune":
            sql_ids = [args.sql_id] if args.sql_id else [s.sql_id for s in discovery.discover(config.agent.max_sql, config.agent.ranking_metric)]
            advisor = SqlTuningAdvisor(connection)
            parser_obj = RecommendationParser()
            for sql_id in sql_ids:
                if not discovery.validate_sql_id_exists(sql_id):
                    LOGGER.warning("SQL_ID %s no longer exists in V$SQL; skipping", sql_id)
                    continue
                result = advisor.tune_sql_id(sql_id, drop_after=config.agent.drop_tuning_task_after_completion)
                audit.record_tuning_task(result)
                audit.record_recommendations(parser_obj.parse(result))
            return 0

        if args.command == "recommend":
            advisor = SqlTuningAdvisor(connection)
            parser_obj = RecommendationParser()
            statements = discovery.discover(config.agent.max_sql, config.agent.ranking_metric)
            all_recommendations = []
            for stmt in statements:
                result = advisor.tune_sql_id(stmt.sql_id, drop_after=config.agent.drop_tuning_task_after_completion)
                recs = parser_obj.parse(result)
                audit.record_tuning_task(result)
                audit.record_recommendations(recs)
                all_recommendations.extend(recs)
            print(render_recommendations(all_recommendations))
            return 0

        if args.command == "apply":
            from .models import Recommendation, RecommendationType, RiskLevel

            rec = Recommendation(
                sql_id=args.sql_id,
                task_name=args.task_name,
                type=RecommendationType(args.type),
                summary="CLI-approved implementation request",
                findings="Loaded from prior tuning task/audit record by operator context.",
                recommended_solution="Accept SQL profile from DBMS_SQLTUNE task.",
                expected_benefit=None,
                risk_level=RiskLevel.LOW if args.type == "SQL_PROFILE" else RiskLevel.MEDIUM,
                required_privileges=["ADMINISTER SQL MANAGEMENT OBJECT"],
                rollback_plan="Drop SQL profile with DBMS_SQLTUNE.DROP_SQL_PROFILE.",
                automated=args.type == "SQL_PROFILE",
                raw_text="",
            )
            implementer = RecommendationImplementer(connection, PolicyGate(config.agent), audit, discovery)
            action = implementer.apply(rec, approved=args.approved)
            print(f"{action.status}: {action.details}")
            return 0

        if args.command == "rollback":
            implementer = RecommendationImplementer(connection, PolicyGate(config.agent), audit, discovery)
            action = implementer.rollback_sql_profile(args.profile_name, args.sql_id)
            print(f"{action.status}: {action.details}")
            return 0

        if args.command == "report":
            rows = audit.fetch_recent_recommendations(limit=50)
            if not rows:
                print("No recommendations found in audit tables.")
                return 0
            for row in rows:
                print(
                    "{created_at} sql_id={sql_id} risk={risk_level} type={recommendation_type} "
                    "automated={automated} status={status} benefit={expected_benefit} summary={summary}".format(**row)
                )
            return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
