from __future__ import annotations

from .config import RollbackThreshold
from .models import PerformanceBaseline


def degradation_reasons(
    before: PerformanceBaseline,
    after: PerformanceBaseline,
    threshold: RollbackThreshold,
) -> list[str]:
    if after.executions < threshold.min_executions:
        return []
    reasons: list[str] = []
    elapsed_pct = _pct_increase(before.avg_elapsed_time, after.avg_elapsed_time)
    cpu_pct = _pct_increase(before.avg_cpu_time, after.avg_cpu_time)
    if elapsed_pct > threshold.elapsed_time_pct:
        reasons.append(f"avg elapsed time increased by {elapsed_pct:.1f}%")
    if cpu_pct > threshold.cpu_time_pct:
        reasons.append(f"avg CPU time increased by {cpu_pct:.1f}%")
    return reasons


def _pct_increase(before: float, after: float) -> float:
    if before <= 0:
        return 0.0
    return ((after - before) / before) * 100
