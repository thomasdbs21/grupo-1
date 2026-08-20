from __future__ import annotations

from ios_auditor.domain import (
    AnalysisResult,
    FullDeviceAnalysisResult,
    RuleEvaluation,
)
from ios_auditor.domain.models import (
    OperationalContext,
    ShowIpInterfaceBriefData,
    ShowIpSshData,
    ShowVersionData,
)
from ios_auditor.rules import get_interface_operational_rule
from ios_auditor.services.analyzer import analyze_bytes
from ios_auditor.services.evidence_batch import ValidatedEvidenceBatch
from ios_auditor.services.operational_analysis import parse_collected_show_evidence
from ios_auditor.services.rule_results import findings_from_evaluations


_RUNNING_CONFIG_COMMAND = "show running-config"
_RUNNING_CONFIG_SOURCE = "full-device-running-config"
_OPERATIONAL_COMMAND_MODELS = (
    ("show version", ShowVersionData),
    ("show ip interface brief", ShowIpInterfaceBriefData),
    ("show ip ssh", ShowIpSshData),
)


class FullDeviceAnalysisContractError(ValueError):
    """Un analizador puro incumplió el contrato integral esperado."""


def analyze_validated_evidence_batch(
    batch: ValidatedEvidenceBatch,
) -> FullDeviceAnalysisResult:
    """Analiza un lote validado sin recopilar datos ni abrir conexiones."""

    if not isinstance(batch, ValidatedEvidenceBatch):
        raise TypeError("El lote validado es incompatible.")

    running_config_evidence = batch.evidence_for(_RUNNING_CONFIG_COMMAND)
    configuration_result = analyze_bytes(
        running_config_evidence.raw_output.encode("utf-8"),
        source_name=_RUNNING_CONFIG_SOURCE,
    )
    _validate_configuration_result(
        configuration_result,
        running_config_evidence.sha256,
    )

    operational_results = tuple(
        _parse_operational_evidence(batch, command, expected_model)
        for command, expected_model in _OPERATIONAL_COMMAND_MODELS
    )
    interface_context = _operational_result_for(
        operational_results,
        "show ip interface brief",
    )
    operational_evaluation = get_interface_operational_rule().evaluate(
        interface_context
    )
    if not isinstance(operational_evaluation, RuleEvaluation):
        raise FullDeviceAnalysisContractError(
            "La regla operacional produjo una evaluación incompatible."
        )
    operational_evaluations = (operational_evaluation,)
    operational_findings = findings_from_evaluations(operational_evaluations)

    return FullDeviceAnalysisResult(
        execution_id=batch.execution_id,
        evidences=batch.evidences,
        configuration_result=configuration_result,
        operational_results=operational_results,
        operational_evaluations=operational_evaluations,
        operational_findings=operational_findings,
    )


def _validate_configuration_result(
    result: AnalysisResult,
    evidence_sha256: str,
) -> None:
    if not isinstance(result, AnalysisResult) or result.sha256 != evidence_sha256:
        raise FullDeviceAnalysisContractError(
            "El análisis de configuración produjo un resultado incompatible."
        )


def _parse_operational_evidence(
    batch: ValidatedEvidenceBatch,
    command: str,
    expected_model: type[
        ShowVersionData | ShowIpInterfaceBriefData | ShowIpSshData
    ],
) -> OperationalContext:
    evidence = batch.evidence_for(command)
    context = parse_collected_show_evidence(evidence)
    if (
        not isinstance(context, OperationalContext)
        or context.execution_id != batch.execution_id
        or context.command != command
        or context.device_host != evidence.device_host
        or context.collected_at is not evidence.collected_at
        or context.sha256 != evidence.sha256
        or not isinstance(context.data, expected_model)
    ):
        raise FullDeviceAnalysisContractError(
            "El análisis operacional produjo un resultado incompatible."
        )
    return context


def _operational_result_for(
    results: tuple[OperationalContext, ...],
    command: str,
) -> OperationalContext:
    for result in results:
        if result.command == command:
            return result
    raise FullDeviceAnalysisContractError(
        "Falta un resultado operacional requerido."
    )


__all__ = [
    "FullDeviceAnalysisContractError",
    "analyze_validated_evidence_batch",
]
