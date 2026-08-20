"""Transformación explícita del resultado integral a un DTO API seguro."""

from __future__ import annotations

from collections import Counter

from ios_auditor.api.schemas import (
    CommandEvidenceMetadataResponse,
    EvidenceResponse,
    FindingResponse,
    FullDeviceAnalysisResponse,
    RuleEvaluationResponse,
)
from ios_auditor.collectors import CommandEvidence
from ios_auditor.domain import (
    Evidence,
    Finding,
    FullDeviceAnalysisResult,
    RuleEvaluation,
)
from ios_auditor.services import CANONICAL_EVIDENCE_COMMANDS
from ios_auditor.services.rule_results import findings_from_evaluations


class FullDeviceResponseContractError(ValueError):
    """El resultado integral no cumple el contrato de respuesta segura."""


def to_full_device_analysis_response(
    result: FullDeviceAnalysisResult,
) -> FullDeviceAnalysisResponse:
    """Crea un DTO sanitizado sin serializar evidencias o contextos completos."""

    if not isinstance(result, FullDeviceAnalysisResult):
        raise FullDeviceResponseContractError(
            "El resultado integral es incompatible con la respuesta API."
        )

    evidences = result.evidences
    if (
        len(evidences) != len(CANONICAL_EVIDENCE_COMMANDS)
        or not all(isinstance(evidence, CommandEvidence) for evidence in evidences)
        or tuple(evidence.command for evidence in evidences)
        != CANONICAL_EVIDENCE_COMMANDS
    ):
        raise FullDeviceResponseContractError(
            "Las evidencias integrales no cumplen el contrato canónico."
        )
    if any(evidence.execution_id != result.execution_id for evidence in evidences):
        raise FullDeviceResponseContractError(
            "Las evidencias no comparten el identificador integral."
        )

    evaluations = result.evaluations
    findings = result.findings
    if findings != findings_from_evaluations(evaluations):
        raise FullDeviceResponseContractError(
            "Los hallazgos no corresponden con las evaluaciones FAIL."
        )

    return FullDeviceAnalysisResponse(
        execution_id=result.execution_id,
        evidences=[
            CommandEvidenceMetadataResponse(
                command=evidence.command,
                collected_at=evidence.collected_at,
                raw_output_sha256=evidence.sha256,
            )
            for evidence in evidences
        ],
        operational_context_count=len(result.operational_results),
        rule_evaluations=[
            _rule_evaluation_response(evaluation) for evaluation in evaluations
        ],
        findings=[_finding_response(finding) for finding in findings],
        total_evaluations=len(evaluations),
        total_findings=len(findings),
        status_summary=dict(Counter(evaluation.status for evaluation in evaluations)),
        finding_severity_summary=dict(
            Counter(finding.severity for finding in findings)
        ),
    )


def _evidence_response(evidence: Evidence) -> EvidenceResponse:
    return EvidenceResponse(
        source=evidence.source,
        sha256=evidence.sha256,
        line_number=evidence.line_number,
        content=evidence.content,
    )


def _rule_evaluation_response(
    evaluation: RuleEvaluation,
) -> RuleEvaluationResponse:
    return RuleEvaluationResponse(
        rule_id=evaluation.rule_id,
        rule_name=evaluation.rule_name,
        status=evaluation.status,
        severity=evaluation.severity,
        message=evaluation.message,
        recommendation=evaluation.recommendation,
        evidence=[_evidence_response(item) for item in evaluation.evidence],
    )


def _finding_response(finding: Finding) -> FindingResponse:
    return FindingResponse(
        rule_id=finding.rule_id,
        rule_name=finding.rule_name,
        severity=finding.severity,
        message=finding.message,
        recommendation=finding.recommendation,
        evidence=[_evidence_response(item) for item in finding.evidence],
    )


__all__ = [
    "FullDeviceResponseContractError",
    "to_full_device_analysis_response",
]
