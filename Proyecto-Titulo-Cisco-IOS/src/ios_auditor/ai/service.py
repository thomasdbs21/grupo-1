from __future__ import annotations

import re
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from ios_auditor.domain import Finding

from .contracts import AIContext, Explanation, ExplanationResponse, FindingContext
from .errors import AIError, AIErrorCode
from .prompts import build_messages
from .sanitization import (
    MAX_CONTEXT_BYTES, MAX_EVIDENCE_CHARACTERS, MAX_EVIDENCE_PER_FINDING,
    MAX_FINDINGS, bounded_text,
)
from .settings import AISettings


class ExplanationProvider(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...
    def reachable(self) -> bool: ...


def build_context(analysis_id: UUID, findings: tuple[Finding, ...]) -> AIContext:
    """Única frontera de entrada: objetos Finding del motor; nunca DTO enviado por la UI."""
    selected: list[FindingContext] = []
    used = 0
    for finding in findings[:MAX_FINDINGS]:
        if not isinstance(finding, Finding):
            raise TypeError("Se requieren Findings deterministas.")
        safe = FindingContext(
            rule_id=finding.rule_id, rule_name=bounded_text(finding.rule_name, 160),
            severity=finding.severity.value, message=bounded_text(finding.message, 500),
            recommendation=bounded_text(finding.recommendation, 500),
            evidence=tuple(bounded_text(e.content, MAX_EVIDENCE_CHARACTERS)
                           for e in finding.evidence[:MAX_EVIDENCE_PER_FINDING]),
        )
        cost = len(safe.model_dump_json().encode("utf-8")) + 2
        if used + cost > MAX_CONTEXT_BYTES - 1024:
            break
        selected.append(safe)
        used += cost
    return AIContext(analysis_id=analysis_id, findings=tuple(selected),
                     total_findings=len(findings), truncated=len(selected) < len(findings))


class ExplanationService:
    def __init__(self, settings: AISettings, provider: ExplanationProvider):
        self.settings = settings
        self.provider = provider

    def explain(self, context: AIContext, question: str | None = None) -> ExplanationResponse:
        if not context.total_findings:
            return ExplanationResponse(
                analysis_id=context.analysis_id, source="deterministic", context_truncated=False,
                explanation=Explanation(summary="No existen Findings deterministas para explicar.",
                                        findings=(), limitations=(), question_answer=(
                                            "Este análisis no contiene hallazgos para responder la pregunta."
                                            if question else None)),
            )
        if not self.settings.enabled:
            raise AIError(AIErrorCode.DISABLED)
        if not context.findings:
            raise AIError(AIErrorCode.INVALID_RESPONSE)
        messages = build_messages(context, question)
        explanation = None
        for repair in range(2):
            try:
                raw = self.provider.complete(messages)
                explanation = Explanation.model_validate_json(raw)
                break
            except ValidationError:
                if repair:
                    raise AIError(AIErrorCode.INVALID_RESPONSE) from None
                # Una sola reparación; no reenvía una respuesta inválida o potencialmente sensible.
                messages = messages + [{"role": "user", "content": "Devuelve solo el JSON de OUTPUT_SCHEMA, con todos los campos requeridos y sin campos extra."}]
            except AIError as exc:
                if exc.code != AIErrorCode.INVALID_RESPONSE or repair:
                    raise
                messages = messages + [{"role": "user", "content": "Devuelve solo JSON válido según OUTPUT_SCHEMA."}]
        if explanation is None:
            raise AIError(AIErrorCode.INVALID_RESPONSE)
        expected = {f.rule_id for f in context.findings}
        actual = [f.rule_id for f in explanation.findings]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise AIError(AIErrorCode.INVALID_RESPONSE)
        rendered = explanation.model_dump_json()
        if re.search(r"(?i)\b(?:configure\s+terminal|conf\s+t|send_config_set|config_mode|write\s+memory|reload)\b", rendered):
            raise AIError(AIErrorCode.INVALID_RESPONSE)
        if question and not explanation.question_answer:
            raise AIError(AIErrorCode.INVALID_RESPONSE)
        return ExplanationResponse(analysis_id=context.analysis_id, source="ai",
                                   context_truncated=context.truncated, explanation=explanation)
