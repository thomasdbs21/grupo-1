"""Frontera entre evidencia recopilada y parsing operacional."""

from __future__ import annotations

import hashlib
from datetime import timedelta

from ios_auditor.collectors import CommandEvidence
from ios_auditor.domain.models import OperationalContext
from ios_auditor.parsers import (
    SUPPORTED_SHOW_COMMANDS,
    ShowCommandParseError,
    normalize_show_output,
    parse_show_command,
)


class OperationalAnalysisError(Exception):
    """Error público y seguro del análisis operacional."""


class OperationalEvidenceError(OperationalAnalysisError):
    """La evidencia no cumple el contrato requerido para ser procesada."""


def parse_collected_show_evidence(evidence: CommandEvidence) -> OperationalContext:
    """Valida la evidencia y construye un contexto operacional inmutable."""

    if not isinstance(evidence, CommandEvidence):
        raise OperationalEvidenceError("La evidencia operacional es incompatible.")

    normalized_command = evidence.command.strip().lower()
    if normalized_command not in SUPPORTED_SHOW_COMMANDS:
        raise OperationalEvidenceError("El comando de la evidencia no está soportado.")

    raw_sha256 = hashlib.sha256(evidence.raw_output.encode("utf-8")).hexdigest()
    if raw_sha256 != evidence.sha256:
        raise OperationalEvidenceError(
            "La evidencia operacional no supera la verificación de integridad."
        )
    if normalize_show_output(evidence.raw_output) != evidence.normalized_output:
        raise OperationalEvidenceError(
            "La salida normalizada no corresponde con la evidencia original."
        )
    if (
        evidence.collected_at.tzinfo is None
        or evidence.collected_at.utcoffset() != timedelta(0)
    ):
        raise OperationalEvidenceError(
            "La fecha de recopilación debe estar expresada en UTC."
        )

    try:
        data = parse_show_command(normalized_command, evidence.normalized_output)
    except ShowCommandParseError:
        raise OperationalAnalysisError(
            "No fue posible estructurar la evidencia operacional."
        ) from None

    return OperationalContext(
        execution_id=evidence.execution_id,
        device_host=evidence.device_host,
        command=normalized_command,
        collected_at=evidence.collected_at,
        sha256=evidence.sha256,
        data=data,
    )
