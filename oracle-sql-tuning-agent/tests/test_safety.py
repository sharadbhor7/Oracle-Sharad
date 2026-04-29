from datetime import datetime

from sqltune_agent.config import RollbackThreshold
from sqltune_agent.models import PerformanceBaseline
from sqltune_agent.safety import degradation_reasons


def _baseline(cpu, elapsed, executions=20):
    return PerformanceBaseline(
        sql_id="abc123",
        plan_hash_value=1,
        executions=executions,
        avg_cpu_time=cpu,
        avg_elapsed_time=elapsed,
        buffer_gets=1,
        disk_reads=1,
        captured_at=datetime.utcnow(),
    )


def test_degradation_detects_cpu_and_elapsed_thresholds():
    reasons = degradation_reasons(
        _baseline(cpu=100, elapsed=100),
        _baseline(cpu=130, elapsed=125),
        RollbackThreshold(cpu_time_pct=20, elapsed_time_pct=20, min_executions=10),
    )

    assert "avg elapsed time increased" in reasons[0]
    assert "avg CPU time increased" in reasons[1]


def test_degradation_waits_for_minimum_executions():
    reasons = degradation_reasons(
        _baseline(cpu=100, elapsed=100),
        _baseline(cpu=200, elapsed=200, executions=1),
        RollbackThreshold(min_executions=10),
    )

    assert reasons == []
