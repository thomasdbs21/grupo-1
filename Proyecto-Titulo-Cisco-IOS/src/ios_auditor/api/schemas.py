from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address, IPv4Network
from typing import Annotated, Literal
from unicodedata import category
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from ios_auditor.domain import RuleStatus, Severity
from ios_auditor.services.evidence_batch import CANONICAL_EVIDENCE_COMMANDS


# Base de los contratos HTTP con validación de campos de entrada y salida.
class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


_RFC1918_NETWORKS = (
    IPv4Network("10.0.0.0/8"),
    IPv4Network("172.16.0.0/12"),
    IPv4Network("192.168.0.0/16"),
)
_CANONICAL_COMMANDS = CANONICAL_EVIDENCE_COMMANDS
MAX_DEVICE_USERNAME_LENGTH = 128
MAX_DEVICE_PASSWORD_LENGTH = 1024


# El contrato de entrada delimita qué información puede entregar el cliente para la sesión de lectura.
# Contrato de la sesión de adquisición con destino y credenciales transitorias.
class DeviceAnalysisRequest(ApiModel):
    host: IPv4Address
    port: Annotated[int, Field(strict=True, ge=1, le=65535)]
    username: Annotated[
        str,
        Field(min_length=1, max_length=MAX_DEVICE_USERNAME_LENGTH),
    ]
    password: Annotated[
        SecretStr,
        Field(min_length=1, max_length=MAX_DEVICE_PASSWORD_LENGTH),
    ]

    # Restringe el destino del análisis de dispositivo al contrato IPv4 privado de la API.
    @field_validator("host")
    @classmethod
    def validate_private_ipv4(cls, value: IPv4Address) -> IPv4Address:
        matching_network = next(
            (network for network in _RFC1918_NETWORKS if value in network),
            None,
        )
        # Sin prefijo no puede inferirse si .0 o .255 representan red o broadcast;
        # se excluyen como restricción conservadora de destino del MVP.
        if (
            matching_network is None
            or value
            in {
                matching_network.network_address,
                matching_network.broadcast_address,
            }
            or value.packed[-1] in {0, 255}
        ):
            raise ValueError(
                "El host no cumple la política de destinos IPv4 RFC 1918 del MVP."
            )
        return value

    # Valida el formato del usuario antes de delegar la conexión al collector.
    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if value != value.strip() or any(category(char) == "Cc" for char in value):
            raise ValueError("El usuario contiene caracteres no permitidos.")
        return value


# Código y mensaje público de una solicitud que no pudo completarse.
class ErrorDetail(ApiModel):
    code: str
    message: str


# Envoltorio común de los errores de la API.
class ErrorResponse(ApiModel):
    error: ErrorDetail


# Disponibilidad y versión del servicio consultadas por los clientes.
class HealthResponse(ApiModel):
    status: Literal["ok"]
    service: str
    version: str


# Metadatos del catálogo que el cliente puede consultar sin ejecutar reglas.
class RuleSummaryResponse(ApiModel):
    id: str
    version: str
    name: str
    category: str
    default_severity: Severity
    description: str
    required_sources: list[str]


# Fragmento y referencias de evidencia que acompañan al resultado público.
class EvidenceResponse(ApiModel):
    source: str
    sha256: str
    line_number: int | None
    content: str


# Representación HTTP de un resultado individual de regla.
class RuleEvaluationResponse(ApiModel):
    rule_id: str
    rule_name: str
    status: RuleStatus
    severity: Severity
    message: str
    recommendation: str
    evidence: list[EvidenceResponse]


# Representación HTTP de un hallazgo derivado de FAIL.
class FindingResponse(ApiModel):
    rule_id: str
    rule_name: str
    severity: Severity
    message: str
    recommendation: str
    evidence: list[EvidenceResponse]


CanonicalCommand = Literal[
    "show running-config",
    "show version",
    "show ip interface brief",
    "show ip ssh",
    "show interfaces",
    "show access-lists",
    "show ntp associations",
    "show ip ospf neighbor",
]


# Metadatos públicos de la consulta, conservando fuera las salidas crudas.
class CommandEvidenceMetadataResponse(ApiModel):
    command: CanonicalCommand
    collected_at: datetime
    raw_output_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


# Respuesta agregada del análisis de configuración y fuentes operacionales.
class FullDeviceAnalysisResponse(ApiModel):
    execution_id: UUID
    evidences: Annotated[
        list[CommandEvidenceMetadataResponse],
        Field(min_length=len(_CANONICAL_COMMANDS), max_length=len(_CANONICAL_COMMANDS)),
    ]
    operational_context_count: Annotated[int, Field(ge=0)]
    rule_evaluations: list[RuleEvaluationResponse]
    findings: list[FindingResponse]
    total_evaluations: Annotated[int, Field(ge=0)]
    total_findings: Annotated[int, Field(ge=0)]
    status_summary: dict[RuleStatus, Annotated[int, Field(ge=0)]]
    finding_severity_summary: dict[Severity, Annotated[int, Field(ge=0)]]


# Resultado almacenado y contadores que consume la interfaz.
class AnalysisResponse(ApiModel):
    analysis_id: str
    source_name: str
    sha256: str
    created_at: datetime
    status: Literal["COMPLETED"]
    evaluations: list[RuleEvaluationResponse]
    findings: list[FindingResponse]
    total_evaluations: int
    total_findings: int
    status_summary: dict[str, int]
    finding_severity_summary: dict[str, int]


# Respuesta de creación del análisis por archivo.
class AnalysisCreatedResponse(AnalysisResponse):
    pass
