from __future__ import annotations

from .models import Recommendation


def render_recommendations(recommendations: list[Recommendation]) -> str:
    lines: list[str] = []
    for rec in recommendations:
        lines.extend(
            [
                f"SQL_ID: {rec.sql_id}",
                f"Risk: {rec.risk_level.value}",
                f"Type: {rec.type.value}",
                f"Summary: {rec.summary}",
                f"Expected benefit: {rec.expected_benefit or 'Not quantified by advisor'}",
                f"Automated: {'yes' if rec.automated else 'no'}",
                f"Required privileges: {', '.join(rec.required_privileges)}",
                f"Rollback: {rec.rollback_plan}",
                "",
            ]
        )
    return "\n".join(lines).strip()
