from __future__ import annotations

import hashlib
from pathlib import Path

from ios_auditor.domain import (
    AnalysisResult,
    Finding,
    RuleEvaluation,
    RuleStatus,
)
from ios_auditor.parsers import parse_running_config
from ios_auditor.rules import RuleRegistry, get_default_registry
from ios_auditor.rules.base import Rule


class AnalysisError(Exception):
    """Error comprensible producido antes de completar un análisis."""


def load_context(path_value: str | Path):
    path = Path(path_value)
    if not path.exists():
        raise AnalysisError(f"El archivo no existe: {path}")
    if not path.is_file():
        raise AnalysisError(f"La ruta no corresponde a un archivo regular: {path}")

    try:
        raw = path.read_bytes()
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AnalysisError(f"El archivo no está codificado en UTF-8: {path}") from exc
    except OSError as exc:
        raise AnalysisError(f"No fue posible leer el archivo: {path}") from exc

    if not content.strip():
        raise AnalysisError(f"El archivo está vacío: {path}")

    sha256 = hashlib.sha256(raw).hexdigest()
    try:
        return parse_running_config(
            source_path=path.resolve(), content=content, sha256=sha256
        )
    except Exception as exc:
        raise AnalysisError(f"No fue posible procesar la configuración: {path}") from exc


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
    active_registry = registry or get_default_registry()
    evaluations = tuple(
        _evaluate_rule(rule, context)
        for rule in active_registry.list_rules(enabled_only=True)
    )
    findings = tuple(
        Finding(
            rule_id=evaluation.rule_id,
            rule_name=evaluation.rule_name,
            severity=evaluation.severity,
            message=evaluation.message,
            recommendation=evaluation.recommendation,
            evidence=evaluation.evidence,
        )
        for evaluation in evaluations
        if evaluation.status is RuleStatus.FAIL
    )
    return AnalysisResult(
        source_path=context.source_path,
        sha256=context.sha256,
        evaluations=evaluations,
        findings=findings,
    )
