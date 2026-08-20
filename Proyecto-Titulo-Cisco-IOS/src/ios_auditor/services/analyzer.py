from __future__ import annotations

import hashlib
from pathlib import Path

from ios_auditor.domain import (
    AnalysisResult,
    RuleEvaluation,
    RuleStatus,
)
from ios_auditor.parsers import parse_running_config
from ios_auditor.rules import RuleRegistry, get_default_registry
from ios_auditor.rules.base import Rule
from ios_auditor.services.rule_results import findings_from_evaluations


class AnalysisError(Exception):
    """Error comprensible producido antes de completar un análisis."""


class EmptyContentError(AnalysisError):
    """El contenido recibido no contiene una configuración."""


class InvalidEncodingError(AnalysisError):
    """El contenido no es texto UTF-8 válido."""


class UnanalyzableConfigError(AnalysisError):
    """El parser no pudo procesar la configuración."""


def load_context_from_bytes(raw: bytes, *, source_name: str):
    if b"\x00" in raw:
        raise InvalidEncodingError("El contenido parece binario y no puede analizarse.")

    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidEncodingError("El contenido no está codificado en UTF-8.") from exc

    if not content.strip():
        raise EmptyContentError("El archivo está vacío.")

    sha256 = hashlib.sha256(raw).hexdigest()
    try:
        return parse_running_config(
            source_path=Path(source_name), content=content, sha256=sha256
        )
    except (ValueError, TypeError, OSError) as exc:
        raise UnanalyzableConfigError(
            "No fue posible procesar la configuración."
        ) from exc


def load_context(path_value: str | Path):
    path = Path(path_value)
    if not path.exists():
        raise AnalysisError(f"El archivo no existe: {path}")
    if not path.is_file():
        raise AnalysisError(f"La ruta no corresponde a un archivo regular: {path}")

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AnalysisError(f"No fue posible leer el archivo: {path}") from exc
    try:
        return load_context_from_bytes(raw, source_name=str(path.resolve()))
    except EmptyContentError as exc:
        raise EmptyContentError(f"El archivo está vacío: {path}") from exc
    except InvalidEncodingError as exc:
        raise InvalidEncodingError(
            f"El archivo no está codificado en UTF-8: {path}"
        ) from exc
    except UnanalyzableConfigError as exc:
        raise UnanalyzableConfigError(
            f"No fue posible procesar la configuración: {path}"
        ) from exc


def _evaluate_rule(rule: Rule, context) -> RuleEvaluation:
    try:
        return rule.evaluate(context)
    except Exception as exc:
        return RuleEvaluation(
            rule_id=rule.metadata.id,
            rule_name=rule.metadata.name,
            status=RuleStatus.ERROR,
            severity=rule.metadata.default_severity,
            message=f"Error interno al evaluar la regla: {type(exc).__name__}",
            recommendation=rule.metadata.recommendation,
        )


def analyze_file(
    path_value: str | Path, *, registry: RuleRegistry | None = None
) -> AnalysisResult:
    context = load_context(path_value)
    return analyze_context(context, registry=registry)


def analyze_bytes(
    raw: bytes, *, source_name: str, registry: RuleRegistry | None = None
) -> AnalysisResult:
    context = load_context_from_bytes(raw, source_name=source_name)
    return analyze_context(context, registry=registry)


def analyze_context(context, *, registry: RuleRegistry | None = None) -> AnalysisResult:
    active_registry = registry or get_default_registry()
    evaluations = tuple(
        _evaluate_rule(rule, context)
        for rule in active_registry.list_rules(enabled_only=True)
    )
    findings = findings_from_evaluations(evaluations)
    return AnalysisResult(
        source_path=context.source_path,
        sha256=context.sha256,
        evaluations=evaluations,
        findings=findings,
    )
