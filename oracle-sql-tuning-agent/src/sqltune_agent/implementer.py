from __future__ import annotations

import re
from datetime import datetime

from .audit import AuditRepository
from .discovery import WorkloadDiscovery
from .models import ImplementationAction, PerformanceBaseline, Recommendation, RecommendationType
from .policy import PolicyGate


class RecommendationImplementer:
    def __init__(
        self,
        connection: object,
        policy: PolicyGate,
        audit: AuditRepository,
        discovery: WorkloadDiscovery,
    ):
        self.connection = connection
        self.policy = policy
        self.audit = audit
        self.discovery = discovery

    def apply(self, recommendation: Recommendation, approved: bool = False) -> ImplementationAction:
        decision = self.policy.can_apply(recommendation, approved=approved)
        if not decision.allowed:
            action = ImplementationAction(
                sql_id=recommendation.sql_id,
                recommendation_type=recommendation.type,
                action_name="POLICY_GATE",
                status="BLOCKED",
                details=decision.reason,
            )
            self.audit.record_implementation_action(action)
            return action

        before = self.discovery.capture_baseline(recommendation.sql_id)
        if recommendation.type == RecommendationType.SQL_PROFILE:
            action = self._accept_sql_profile(recommendation, before)
        else:
            action = ImplementationAction(
                sql_id=recommendation.sql_id,
                recommendation_type=recommendation.type,
                action_name="MANUAL_IMPLEMENTATION_REQUIRED",
                status="BLOCKED",
                details="This recommendation type is not automated by the agent.",
            )
        self.audit.record_implementation_action(action)
        return action

    def rollback_sql_profile(self, profile_name: str, sql_id: str) -> ImplementationAction:
        cursor = self.connection.cursor()
        cursor.execute(
            "begin dbms_sqltune.drop_sql_profile(name => :profile_name, ignore => true); end;",
            {"profile_name": profile_name},
        )
        self.connection.commit()
        action = ImplementationAction(
            sql_id=sql_id,
            recommendation_type=RecommendationType.SQL_PROFILE,
            action_name="DROP_SQL_PROFILE",
            status="ROLLED_BACK",
            details=f"Dropped SQL profile {profile_name}",
            rollback_token=profile_name,
        )
        self.audit.record_implementation_action(action)
        self.audit.record_rollback_action(
            sql_id=sql_id,
            rollback_type="DROP_SQL_PROFILE",
            rollback_token=profile_name,
            status="ROLLED_BACK",
            details=f"Dropped SQL profile {profile_name}",
        )
        return action

    def _accept_sql_profile(
        self,
        recommendation: Recommendation,
        before: PerformanceBaseline | None,
    ) -> ImplementationAction:
        profile_name = f"SQLTUNE_{recommendation.sql_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        task_name = _safe_identifier(recommendation.task_name)
        cursor = self.connection.cursor()
        cursor.execute(
            """
            begin
              dbms_sqltune.accept_sql_profile(
                task_name => :task_name,
                name => :profile_name,
                replace => false,
                force_match => false
              );
            end;
            """,
            {"task_name": task_name, "profile_name": profile_name},
        )
        self.connection.commit()
        baseline_note = f" before_avg_elapsed={before.avg_elapsed_time}" if before else ""
        return ImplementationAction(
            sql_id=recommendation.sql_id,
            recommendation_type=recommendation.type,
            action_name="ACCEPT_SQL_PROFILE",
            status="APPLIED",
            details=f"Accepted SQL profile {profile_name}.{baseline_note}",
            rollback_token=profile_name,
        )


def _safe_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_$#]+", value):
        raise ValueError(f"Unsafe Oracle identifier: {value}")
    return value
