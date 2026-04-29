from sqltune_agent.config import AgentConfig
from sqltune_agent.models import Recommendation, RecommendationType, RiskLevel
from sqltune_agent.policy import PolicyGate


def _recommendation(risk=RiskLevel.LOW, rec_type=RecommendationType.SQL_PROFILE):
    return Recommendation(
        sql_id="abc123",
        task_name="STA_abc123",
        type=rec_type,
        summary="summary",
        findings="findings",
        recommended_solution="solution",
        expected_benefit=None,
        risk_level=risk,
        required_privileges=[],
        rollback_plan="rollback",
        automated=True,
        raw_text="",
    )


def test_advisory_only_blocks_apply():
    gate = PolicyGate(AgentConfig(advisory_only=True, auto_apply_low_risk=True))

    decision = gate.can_apply(_recommendation())

    assert decision.allowed is False
    assert "advisory_only" in decision.reason


def test_low_risk_sql_profile_allowed_when_configured():
    gate = PolicyGate(AgentConfig(advisory_only=False, auto_apply_low_risk=True))

    decision = gate.can_apply(_recommendation())

    assert decision.allowed is True


def test_high_risk_never_allowed_even_with_approval():
    gate = PolicyGate(AgentConfig(advisory_only=False, auto_apply_low_risk=True))

    decision = gate.can_apply(_recommendation(RiskLevel.HIGH, RecommendationType.INDEX), approved=True)

    assert decision.allowed is False
    assert "HIGH-risk" in decision.reason
