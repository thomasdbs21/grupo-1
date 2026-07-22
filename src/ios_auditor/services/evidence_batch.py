from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable
from uuid import UUID

from ios_auditor.collectors import ALLOWED_COMMANDS, CommandEvidence
from ios_auditor.parsers import normalize_show_output


CANONICAL_EVIDENCE_COMMANDS = (
    "show running-config",
    "show version",
    "show ip interface brief",
    "show ip ssh",
)

_CANONICAL_COMMAND_SET = frozenset(CANONICAL_EVIDENCE_COMMANDS)
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class EvidenceBatchValidationError(ValueError):
    """Error seguro producido por un lote de evidencias inválido."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ValidatedEvidenceBatch:
    """Lote integral validado, ordenado y libre de datos de conexión."""

    evidences: tuple[CommandEvidence, ...]
    execution_id: UUID = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.evidences, tuple):
            raise EvidenceBatchValidationError(
                "INVALID_BATCH_TYPE",
                "El lote validado requiere una tupla de evidencias.",
            )
        ordered, execution_id = _validate_and_order(self.evidences)
        object.__setattr__(self, "evidences", ordered)
        object.__setattr__(self, "execution_id", execution_id)

    def evidence_for(self, command: str) -> CommandEvidence:
        """Devuelve la evidencia asociada a un comando canónico."""

        try:
            position = CANONICAL_EVIDENCE_COMMANDS.index(command)
        except ValueError:
            raise EvidenceBatchValidationError(
                "UNAUTHORIZED_COMMAND",
                "El comando solicitado no pertenece al contrato del lote.",
            ) from None
        return self.evidences[position]


def validate_evidence_batch(
    evidences: Iterable[CommandEvidence],
) -> ValidatedEvidenceBatch:
    """Valida y ordena las cuatro evidencias de una auditoría integral."""

    try:
        evidence_tuple = tuple(evidences)
    except TypeError:
        raise EvidenceBatchValidationError(
            "INVALID_BATCH_TYPE",
            "El lote de evidencias no es una colección válida.",
        ) from None
    return ValidatedEvidenceBatch(evidence_tuple)


def _validate_and_order(
    evidences: tuple[CommandEvidence, ...],
) -> tuple[tuple[CommandEvidence, ...], UUID]:
    if len(evidences) > len(CANONICAL_EVIDENCE_COMMANDS):
        raise EvidenceBatchValidationError(
            "TOO_MANY_EVIDENCES",
            "El lote contiene más evidencias de las permitidas.",
        )

    if len(evidences) < len(CANONICAL_EVIDENCE_COMMANDS) - 1:
        raise EvidenceBatchValidationError(
            "TOO_FEW_EVIDENCES",
            "El lote contiene menos evidencias de las requeridas.",
        )

    if not all(isinstance(evidence, CommandEvidence) for evidence in evidences):
        raise EvidenceBatchValidationError(
            "INVALID_EVIDENCE_TYPE",
            "El lote contiene un tipo de evidencia no admitido.",
        )

    commands = tuple(evidence.command for evidence in evidences)
    if not all(isinstance(command, str) for command in commands):
        raise EvidenceBatchValidationError(
            "INVALID_COMMAND_TYPE",
            "El lote contiene un comando de tipo inválido.",
        )
    if any(command not in ALLOWED_COMMANDS for command in commands):
        raise EvidenceBatchValidationError(
            "UNAUTHORIZED_COMMAND",
            "El lote contiene un comando no autorizado.",
        )

    if any(command not in _CANONICAL_COMMAND_SET for command in commands):
        raise EvidenceBatchValidationError(
            "UNEXPECTED_COMMAND",
            "El lote contiene un comando ajeno al contrato integral.",
        )

    if len(set(commands)) != len(commands):
        raise EvidenceBatchValidationError(
            "DUPLICATE_COMMAND",
            "El lote contiene un comando duplicado.",
        )

    if len(evidences) < len(CANONICAL_EVIDENCE_COMMANDS):
        raise EvidenceBatchValidationError(
            "MISSING_COMMAND",
            "El lote no contiene todos los comandos requeridos.",
        )

    if frozenset(commands) != _CANONICAL_COMMAND_SET:
        raise EvidenceBatchValidationError(
            "INVALID_COMMAND_SET",
            "El conjunto de comandos del lote no es válido.",
        )

    for evidence in evidences:
        _validate_evidence(evidence)

    execution_id = evidences[0].execution_id
    if any(evidence.execution_id != execution_id for evidence in evidences[1:]):
        raise EvidenceBatchValidationError(
            "MISMATCHED_EXECUTION_ID",
            "Las evidencias no pertenecen a una misma ejecución.",
        )

    evidence_by_command = {evidence.command: evidence for evidence in evidences}
    ordered = tuple(
        evidence_by_command[command] for command in CANONICAL_EVIDENCE_COMMANDS
    )
    return ordered, execution_id


def _validate_evidence(evidence: CommandEvidence) -> None:
    if not isinstance(evidence.execution_id, UUID):
        raise EvidenceBatchValidationError(
            "INVALID_EXECUTION_ID",
            "Una evidencia tiene un identificador de ejecución inválido.",
        )

    if not isinstance(evidence.collected_at, datetime):
        raise EvidenceBatchValidationError(
            "INVALID_COLLECTED_AT",
            "Una evidencia tiene una fecha de recopilación inválida.",
        )

    if evidence.collected_at.tzinfo is None:
        raise EvidenceBatchValidationError(
            "NAIVE_COLLECTED_AT",
            "Una evidencia tiene una fecha sin zona horaria.",
        )

    try:
        utc_offset = evidence.collected_at.utcoffset()
    except Exception:
        raise EvidenceBatchValidationError(
            "INVALID_COLLECTED_AT",
            "Una evidencia tiene una fecha de recopilación inválida.",
        ) from None
    if utc_offset != timedelta(0):
        raise EvidenceBatchValidationError(
            "NON_UTC_COLLECTED_AT",
            "Una evidencia tiene una fecha que no representa UTC.",
        )

    if not isinstance(evidence.raw_output, str) or not isinstance(
        evidence.normalized_output, str
    ):
        raise EvidenceBatchValidationError(
            "INVALID_OUTPUT_TYPE",
            "Una evidencia contiene una salida de tipo inválido.",
        )

    if not isinstance(evidence.sha256, str) or _SHA256_PATTERN.fullmatch(
        evidence.sha256
    ) is None:
        raise EvidenceBatchValidationError(
            "INVALID_SHA256_FORMAT",
            "Una evidencia contiene un SHA-256 con formato inválido.",
        )

    expected_sha256 = hashlib.sha256(evidence.raw_output.encode("utf-8")).hexdigest()
    if evidence.sha256 != expected_sha256:
        raise EvidenceBatchValidationError(
            "SHA256_MISMATCH",
            "La integridad SHA-256 de una evidencia no es válida.",
        )

    if evidence.normalized_output != normalize_show_output(evidence.raw_output):
        raise EvidenceBatchValidationError(
            "NORMALIZED_OUTPUT_MISMATCH",
            "La normalización de una evidencia no es válida.",
        )


__all__ = [
    "CANONICAL_EVIDENCE_COMMANDS",
    "EvidenceBatchValidationError",
    "ValidatedEvidenceBatch",
    "validate_evidence_batch",
]
