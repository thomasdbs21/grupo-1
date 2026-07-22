"""Orquestacion entre recopilacion SSH y analisis determinista existente."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from ios_auditor.collectors import CommandEvidence, NetmikoCollector
from ios_auditor.collectors.netmiko_collector import ConnectionFactory
from ios_auditor.domain import AnalysisResult, FullDeviceAnalysisResult
from ios_auditor.rules import RuleRegistry
from ios_auditor.services.analyzer import analyze_bytes
from ios_auditor.services.evidence_batch import (
    CANONICAL_EVIDENCE_COMMANDS,
    validate_evidence_batch,
)
from ios_auditor.services.full_device_analysis import (
    analyze_validated_evidence_batch,
)


_RUNNING_CONFIG_COMMAND = "show running-config"
_SOURCE_NAME = "ssh-running-config"


class RunningConfigCollector(Protocol):
    """Contrato minimo de un recolector de running-config."""

    def collect(
        self,
        commands: str | Iterable[str],
        *,
        execution_id: UUID | None = None,
    ) -> tuple[CommandEvidence, ...]: ...


class _AnalysisCallable(Protocol):
    def __call__(
        self,
        raw: bytes,
        *,
        source_name: str,
        registry: RuleRegistry | None = None,
    ) -> AnalysisResult: ...


@dataclass(frozen=True, slots=True)
class CollectedAnalysisResult:
    """Mantiene unidas la evidencia recopilada y su analisis."""

    evidence: CommandEvidence
    analysis_result: AnalysisResult

    @property
    def execution_id(self) -> UUID:
        return self.evidence.execution_id


class CollectedAnalysisContractError(Exception):
    """El recolector o el analizador incumplio el contrato de integracion."""


def analyze_collected_running_config(
    collector: RunningConfigCollector,
    *,
    execution_id: UUID | None = None,
    registry: RuleRegistry | None = None,
    analyzer: _AnalysisCallable = analyze_bytes,
) -> CollectedAnalysisResult:
    """Recopila un running-config y lo entrega al analizador en memoria."""

    collected = collector.collect(
        _RUNNING_CONFIG_COMMAND,
        execution_id=execution_id,
    )
    if len(collected) != 1:
        raise CollectedAnalysisContractError(
            "El recolector no devolvio exactamente una evidencia."
        )

    evidence = collected[0]
    if not isinstance(evidence, CommandEvidence):
        raise CollectedAnalysisContractError(
            "El recolector devolvio una evidencia incompatible."
        )
    if evidence.command != _RUNNING_CONFIG_COMMAND:
        raise CollectedAnalysisContractError(
            "El recolector devolvio un comando inesperado."
        )
    if execution_id is not None and evidence.execution_id != execution_id:
        raise CollectedAnalysisContractError(
            "El recolector devolvio un identificador de ejecucion inesperado."
        )

    raw = evidence.raw_output.encode("utf-8")
    if hashlib.sha256(raw).hexdigest() != evidence.sha256:
        raise CollectedAnalysisContractError(
            "La evidencia recopilada no supera la verificacion de integridad."
        )

    analysis_result = analyzer(
        raw,
        source_name=_SOURCE_NAME,
        registry=registry,
    )
    if analysis_result.sha256 != evidence.sha256:
        raise CollectedAnalysisContractError(
            "El resultado del analisis no conserva la integridad de la evidencia."
        )

    return CollectedAnalysisResult(
        evidence=evidence,
        analysis_result=analysis_result,
    )


def collect_and_analyze_device(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    connection_factory: ConnectionFactory | None = None,
) -> FullDeviceAnalysisResult:
    """Recopila y analiza un dispositivo usando una sola sesión de lectura."""

    collector = (
        NetmikoCollector(
            host=host,
            port=port,
            username=username,
            password=password,
        )
        if connection_factory is None
        else NetmikoCollector(
            host=host,
            port=port,
            username=username,
            password=password,
            connection_factory=connection_factory,
        )
    )
    execution_id = uuid4()
    evidences = collector.collect(
        CANONICAL_EVIDENCE_COMMANDS,
        execution_id=execution_id,
    )
    validated_batch = validate_evidence_batch(evidences)
    return analyze_validated_evidence_batch(validated_batch)
