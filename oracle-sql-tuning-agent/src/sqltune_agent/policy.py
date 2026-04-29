from __future__ import annotations

from dataclasses import dataclass

from .config import AgentConfig
from .models import Recommendation, RecommendationType, RiskLevel


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    requires_approval: bool


class PolicyGate:
    def __init__(self, config: AgentConfig):
        self.config = config

    def can_apply(self, recommendation: Recommendation, approved: bool = False) -> PolicyDecision:
        if self.config.advisory_only:
            return PolicyDecision(False, "advisory_only=true prevents implementation", False)
        if recommendation.risk_level == RiskLevel.HIGH:
            return PolicyDecision(False, "HIGH-risk recommendations are never automated", True)
        if recommendation.risk_level == RiskLevel.MEDIUM and not approved:
            return PolicyDecision(False, "MEDIUM-risk recommendations require manual approval", True)
        if recommendation.risk_level == RiskLevel.LOW:
            if recommendation.type != RecommendationType.SQL_PROFILE:
                return PolicyDecision(False, "Only SQL profile acceptance is eligible for LOW-risk automation", True)
            if not self.config.auto_apply_low_risk and not approved:
                return PolicyDecision(False, "auto_apply_low_risk=false requires approval", True)
        return PolicyDecision(True, "Policy allows implementation", recommendation.risk_level != RiskLevel.LOW)
