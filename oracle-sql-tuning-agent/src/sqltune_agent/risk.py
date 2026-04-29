from __future__ import annotations

from .models import RecommendationType, RiskLevel


class RiskScorer:
    HIGH_RISK = {
        RecommendationType.INDEX,
        RecommendationType.SQL_REWRITE,
        RecommendationType.PARTITIONING,
        RecommendationType.MATERIALIZED_VIEW,
        RecommendationType.SCHEMA_CHANGE,
    }
    MEDIUM_RISK = {
        RecommendationType.SQL_PLAN_BASELINE,
        RecommendationType.STATS_REFRESH,
    }

    def score(self, recommendation_type: RecommendationType, raw_text: str) -> RiskLevel:
        lowered = raw_text.lower()
        if recommendation_type in self.HIGH_RISK:
            return RiskLevel.HIGH
        if any(token in lowered for token in ["create index", "alter table", "materialized view", "partition"]):
            return RiskLevel.HIGH
        if recommendation_type in self.MEDIUM_RISK:
            return RiskLevel.MEDIUM
        if recommendation_type == RecommendationType.SQL_PROFILE:
            return RiskLevel.LOW
        return RiskLevel.MEDIUM
