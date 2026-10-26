from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TypeAlias
from uuid import UUID

from ios_auditor.domain.operational_sources import (
    ShowAccessListsData, ShowInterfacesData, ShowIpOspfNeighborData,
    ShowNtpAssociationsData,
)


class Severity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RuleStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_EVALUATED = "NOT_EVALUATED"
    ERROR = "ERROR"


class InterfaceStatus(StrEnum):
    UP = "up"
    DOWN = "down"
    ADMINISTRATIVELY_DOWN = "administratively down"
    DELETED = "deleted"


class ProtocolStatus(StrEnum):
    UP = "up"
    DOWN = "down"


@dataclass(frozen=True, slots=True)
class RuleMetadata:
    id: str
    version: str
    name: str
    category: str
    description: str
    default_severity: Severity
    required_sources: tuple[str, ...]
    applicable_platforms: tuple[str, ...]
    risk: str
    recommendation: str
    references: tuple[str, ...]
    false_positives: tuple[str, ...]
    exceptions: tuple[str, ...]
    enabled: bool


@dataclass(frozen=True, slots=True)
class Evidence:
    source: str
    sha256: str
    line_number: int | None
    content: str


@dataclass(frozen=True, slots=True)
class VtySection:
    header: str
    header_line_number: int
    transport_inputs: tuple[tuple[int, tuple[str, ...]], ...]


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    source_path: str
    sha256: str
    original_content: str
    normalized_lines: tuple[str, ...]
    vty_sections: tuple[VtySection, ...]


@dataclass(frozen=True, slots=True)
class ShowVersionData:
    ios_version: str
    platform: str | None
    software_image: str | None
    uptime: str | None


@dataclass(frozen=True, slots=True)
class InterfaceBriefEntry:
    name: str
    ip_address: str | None
    method: str | None
    status: InterfaceStatus
    protocol: ProtocolStatus


@dataclass(frozen=True, slots=True)
class ShowIpInterfaceBriefData:
    interfaces: tuple[InterfaceBriefEntry, ...]


@dataclass(frozen=True, slots=True)
class ShowIpSshData:
    enabled: bool
    version: str | None
    authentication_timeout_seconds: int | None
    authentication_retries: int | None


ShowCommandData: TypeAlias = (
    ShowVersionData | ShowIpInterfaceBriefData | ShowIpSshData
    | ShowInterfacesData | ShowAccessListsData | ShowNtpAssociationsData
    | ShowIpOspfNeighborData
)


@dataclass(frozen=True, slots=True)
class OperationalContext:
    execution_id: UUID
    device_host: str
    command: str
    collected_at: datetime
    sha256: str
    data: ShowCommandData


@dataclass(frozen=True, slots=True)
class MultiSourceContext:
    configuration: AnalysisContext
    operational: tuple[OperationalContext, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.configuration, AnalysisContext):
            raise TypeError("El contexto de configuración es incompatible.")
        if not isinstance(self.operational, tuple) or not all(
            isinstance(item, OperationalContext) for item in self.operational
        ):
            raise TypeError("Los contextos operacionales requieren una tupla válida.")
        commands = tuple(item.command for item in self.operational)
        if len(commands) != len(set(commands)):
            raise ValueError("No se admiten fuentes operacionales duplicadas.")
        if len({item.execution_id for item in self.operational}) > 1:
            raise ValueError("Las fuentes requieren una ejecución común.")


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    rule_id: str
    rule_name: str
    status: RuleStatus
    severity: Severity
    message: str
    recommendation: str
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str
    rule_name: str
    severity: Severity
    message: str
    recommendation: str
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    source_path: str
    sha256: str
    evaluations: tuple[RuleEvaluation, ...]
    findings: tuple[Finding, ...]
