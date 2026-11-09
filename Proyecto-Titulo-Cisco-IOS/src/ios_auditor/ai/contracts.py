from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .sanitization import sanitize_text

RuleId = Annotated[str, Field(pattern=r"^IOS-[A-Z]+-[0-9]{3}$", max_length=40)]


# Contrato cerrado e inmutable que rechaza campos adicionales en la explicación.
class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# Copia acotada de un hallazgo que puede enviarse al proveedor explicativo.
class FindingContext(ClosedModel):
    rule_id: RuleId
    rule_name: Annotated[str, Field(max_length=160)]
    severity: Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    message: Annotated[str, Field(max_length=500)]
    recommendation: Annotated[str, Field(max_length=500)]
    evidence: Annotated[tuple[str, ...], Field(max_length=2)]


# Agrupa las copias sanitizadas y señala si el conjunto enviado fue truncado.
class AIContext(ClosedModel):
    analysis_id: UUID
    findings: Annotated[tuple[FindingContext, ...], Field(max_length=32)]
    total_findings: Annotated[int, Field(ge=0)]
    truncated: bool = False


# Admite una pregunta opcional con longitud y contenido validados.
class ExplanationRequest(ClosedModel):
    question: Annotated[str, Field(min_length=1, max_length=500)] | None = None

    # Rechaza una pregunta formada solo por espacios antes de enviarla al proveedor.
    @field_validator("question")
    @classmethod
    def nonblank(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("La pregunta no puede estar vacía.")
        return value


# Describe impacto y revisión manual para un único rule_id existente.
class FindingExplanation(ClosedModel):
    rule_id: RuleId
    explanation: Annotated[str, Field(min_length=1, max_length=1500)]
    technical_impact: Annotated[str, Field(min_length=1, max_length=1000)]
    priority_reason: Annotated[str, Field(min_length=1, max_length=1000)]
    manual_review: Annotated[str, Field(min_length=1, max_length=1000)]

    @field_validator("explanation", "technical_impact", "priority_reason", "manual_review")
    @classmethod
    def safe_text(cls, value: str) -> str:
        return sanitize_text(value)


# Esquema del texto generado y de su respuesta opcional a la pregunta.
class Explanation(ClosedModel):
    summary: Annotated[str, Field(min_length=1, max_length=1500)]
    findings: Annotated[tuple[FindingExplanation, ...], Field(max_length=32)]
    limitations: Annotated[tuple[Annotated[str, Field(max_length=1000)], ...], Field(max_length=10)]
    question_answer: Annotated[str, Field(max_length=2000)] | None = None

    @field_validator("summary", "question_answer")
    @classmethod
    def safe_text(cls, value: str | None) -> str | None:
        return sanitize_text(value) if value is not None else None

    @field_validator("limitations")
    @classmethod
    def safe_limitations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sanitize_text(item) for item in value)


# El origen distingue una explicación del modelo de una respuesta determinista sin hallazgos.
# Asocia la explicación validada a su análisis y al origen que la produjo.
class ExplanationResponse(ClosedModel):
    analysis_id: UUID
    source: Literal["ai", "deterministic"]
    context_truncated: bool
    explanation: Explanation


# Expone configuración y accesibilidad HTTP para los indicadores de la interfaz.
class AIHealth(ClosedModel):
    enabled: bool
    gateway_reachable: bool
    model_configured: bool
