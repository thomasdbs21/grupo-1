"""Reglas deterministas aplicadas exclusivamente a contexto operacional."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import ClassVar

from ios_auditor.domain.models import (
    Evidence,
    InterfaceStatus,
    OperationalContext,
    ProtocolStatus,
    RuleEvaluation,
    RuleMetadata,
    RuleStatus,
    ShowIpInterfaceBriefData,
)
from ios_auditor.rules.metadata import load_metadata_files


_INTERFACE_COMMAND = "show ip interface brief"
_METADATA_FILENAME = "IOS-IF-001.yaml"


@dataclass(frozen=True, slots=True)
class InterfaceLineProtocolRule:
    """Detecta interfaces up cuyo protocolo de línea no está up."""

    metadata: RuleMetadata
    expected_id: ClassVar[str] = "IOS-IF-001"

    def evaluate(self, context: object) -> RuleEvaluation:
        if (
            not isinstance(context, OperationalContext)
            or context.command != _INTERFACE_COMMAND
            or not isinstance(context.data, ShowIpInterfaceBriefData)
        ):
            return self._evaluation(
                status=RuleStatus.NOT_APPLICABLE,
                message="La regla requiere un contexto de show ip interface brief.",
            )

        evaluable = tuple(
            interface
            for interface in context.data.interfaces
            if interface.status is not InterfaceStatus.ADMINISTRATIVELY_DOWN
        )
        if not evaluable:
            return self._evaluation(
                status=RuleStatus.NOT_EVALUATED,
                message="No existen interfaces evaluables en la evidencia operacional.",
            )

        inconsistent = tuple(
            interface
            for interface in evaluable
            if interface.status is InterfaceStatus.UP
            and interface.protocol is not ProtocolStatus.UP
        )
        if not inconsistent:
            return self._evaluation(
                status=RuleStatus.PASS,
                message=(
                    "Ninguna interfaz físicamente activa presenta el protocolo "
                    "de línea inactivo."
                ),
            )

        evidence = tuple(
            Evidence(
                source=context.command,
                sha256=context.sha256,
                line_number=None,
                content=(
                    f"interface {interface.name}: status {interface.status.value}, "
                    f"protocol {interface.protocol.value}"
                ),
            )
            for interface in inconsistent
        )
        return self._evaluation(
            status=RuleStatus.FAIL,
            message=(
                "Una o más interfaces están físicamente activas con el "
                "protocolo de línea inactivo."
            ),
            evidence=evidence,
        )

    def _evaluation(
        self,
        *,
        status: RuleStatus,
        message: str,
        evidence: tuple[Evidence, ...] = (),
    ) -> RuleEvaluation:
        return RuleEvaluation(
            rule_id=self.metadata.id,
            rule_name=self.metadata.name,
            status=status,
            severity=self.metadata.default_severity,
            message=message,
            recommendation=self.metadata.recommendation,
            evidence=evidence,
        )


@lru_cache(maxsize=1)
def get_interface_operational_rule() -> InterfaceLineProtocolRule:
    """Carga de forma controlada la regla operacional oficial inicial."""

    resource_directory = Path(str(files("ios_auditor.resources.rules")))
    metadata = load_metadata_files(resource_directory, (_METADATA_FILENAME,))[0]
    if metadata.id != InterfaceLineProtocolRule.expected_id:
        raise ValueError("Los metadatos de IOS-IF-001 son inconsistentes.")
    return InterfaceLineProtocolRule(metadata)
