"""Orquestacion entre recopilacion SSH y analisis determinista existente."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from ios_auditor.collectors import CommandEvidence
from ios_auditor.domain import AnalysisResult
from ios_auditor.rules import RuleRegistry
from ios_auditor.services.analyzer import analyze_bytes


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
