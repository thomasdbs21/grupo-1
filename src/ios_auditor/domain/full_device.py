"""Contrato de dominio para un análisis integral ya procesado."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from ios_auditor.domain.models import (
    AnalysisResult,
    Finding,
    OperationalContext,
    RuleEvaluation,
    RuleStatus,
)

if TYPE_CHECKING:
    from ios_auditor.collectors import CommandEvidence


@dataclass(frozen=True, slots=True)
class FullDeviceAnalysisResult:
    """Compone resultados existentes sin mezclar sus contextos de análisis."""

    execution_id: UUID
    evidences: tuple[CommandEvidence, ...]
    configuration_result: AnalysisResult
    operational_results: tuple[OperationalContext, ...]
    operational_evaluations: tuple[RuleEvaluation, ...]
    operational_findings: tuple[Finding, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.execution_id, UUID):
            raise TypeError("execution_id debe ser un UUID.")
        if not isinstance(self.configuration_result, AnalysisResult):
            raise TypeError("El resultado de configuración es incompatible.")
        if not isinstance(
            self.configuration_result.evaluations, tuple
        ) or not isinstance(self.configuration_result.findings, tuple):
            raise TypeError(
                "Las colecciones del resultado de configuración son inválidas."
            )
        if not all(
            isinstance(evaluation, RuleEvaluation)
            for evaluation in self.configuration_result.evaluations
        ) or not all(
            isinstance(finding, Finding)
            for finding in self.configuration_result.findings
        ):
            raise TypeError(
                "El resultado de configuración contiene objetos incompatibles."
            )

        self._freeze_collection("evidences")
        self._freeze_collection("operational_results")
        self._freeze_collection("operational_evaluations")
        self._freeze_collection("operational_findings")

        if not all(
            isinstance(result, OperationalContext)
            for result in self.operational_results
        ):
            raise TypeError("Los resultados operacionales son incompatibles.")
        if not all(
            isinstance(evaluation, RuleEvaluation)
            for evaluation in self.operational_evaluations
        ):
            raise TypeError("Las evaluaciones operacionales son incompatibles.")
        if not all(
            isinstance(finding, Finding) for finding in self.operational_findings
        ):
            raise TypeError("Los hallazgos operacionales son incompatibles.")

        _validate_findings(
            self.configuration_evaluations,
            self.configuration_findings,
        )
        _validate_findings(
            self.operational_evaluations,
            self.operational_findings,
        )

    def _freeze_collection(self, field_name: str) -> None:
        value = getattr(self, field_name)
        try:
            immutable_value = tuple(value)
        except TypeError:
            raise TypeError(
                "Una colección del resultado integral es inválida."
            ) from None
        object.__setattr__(self, field_name, immutable_value)

    @property
    def configuration_evaluations(self) -> tuple[RuleEvaluation, ...]:
        return self.configuration_result.evaluations

    @property
    def configuration_findings(self) -> tuple[Finding, ...]:
        return self.configuration_result.findings

    @property
    def evaluations(self) -> tuple[RuleEvaluation, ...]:
        return self.configuration_evaluations + self.operational_evaluations

    @property
    def findings(self) -> tuple[Finding, ...]:
        return self.configuration_findings + self.operational_findings


def _validate_findings(
    evaluations: tuple[RuleEvaluation, ...],
    findings: tuple[Finding, ...],
) -> None:
    expected = tuple(
        _finding_from_evaluation(evaluation)
        for evaluation in evaluations
        if evaluation.status is RuleStatus.FAIL
    )
    if findings != expected:
        raise ValueError(
            "Los hallazgos deben corresponder exactamente a evaluaciones FAIL."
        )


def _finding_from_evaluation(evaluation: RuleEvaluation) -> Finding:
    return Finding(
        rule_id=evaluation.rule_id,
        rule_name=evaluation.rule_name,
        severity=evaluation.severity,
        message=evaluation.message,
        recommendation=evaluation.recommendation,
        evidence=evaluation.evidence,
    )
