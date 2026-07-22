from __future__ import annotations

from collections.abc import Iterable

from ios_auditor.domain import Finding, RuleEvaluation, RuleStatus


def findings_from_evaluations(
    evaluations: Iterable[RuleEvaluation],
) -> tuple[Finding, ...]:
    """Deriva hallazgos exclusivamente de evaluaciones FAIL."""

    return tuple(
        Finding(
            rule_id=evaluation.rule_id,
            rule_name=evaluation.rule_name,
            severity=evaluation.severity,
            message=evaluation.message,
            recommendation=evaluation.recommendation,
            evidence=evaluation.evidence,
        )
        for evaluation in evaluations
        if evaluation.status is RuleStatus.FAIL
    )


__all__ = ["findings_from_evaluations"]
