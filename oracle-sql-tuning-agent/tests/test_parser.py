from datetime import datetime

from sqltune_agent.models import RecommendationType, RiskLevel, TuningTaskResult
from sqltune_agent.parser import RecommendationParser


def test_parser_classifies_sql_profile_as_low_risk():
    report = """
Finding 1: SQL Profile Finding
Recommendation (estimated benefit is 91%)
  execute dbms_sqltune.accept_sql_profile(task_name => 'STA_abc', name => 'prof');
"""
    result = TuningTaskResult("abc123", "STA_abc", report, datetime.utcnow())

    recommendations = RecommendationParser().parse(result)

    assert recommendations[0].type == RecommendationType.SQL_PROFILE
    assert recommendations[0].risk_level == RiskLevel.LOW
    assert recommendations[0].automated is True


def test_parser_classifies_index_as_high_risk():
    report = """
Finding 1: Access Path Finding
Recommendation
  Consider running the Access Advisor or create index APP.IDX_ORDERS_1 on APP.ORDERS(CUSTOMER_ID).
"""
    result = TuningTaskResult("def456", "STA_def", report, datetime.utcnow())

    recommendations = RecommendationParser().parse(result)

    assert recommendations[0].type == RecommendationType.INDEX
    assert recommendations[0].risk_level == RiskLevel.HIGH
    assert recommendations[0].automated is False
