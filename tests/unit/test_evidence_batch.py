from __future__ import annotations

import hashlib
import traceback
from collections.abc import Iterator
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone, tzinfo
from uuid import UUID, uuid4

import pytest

from ios_auditor.collectors import ALLOWED_COMMANDS, CommandEvidence
from ios_auditor.services import (
    CANONICAL_EVIDENCE_COMMANDS,
    EvidenceBatchValidationError,
    ValidatedEvidenceBatch,
    validate_evidence_batch,
)


DEVICE = "device.example.invalid"


def _evidence(
    command: str,
    *,
    execution_id: UUID | object | None = None,
    collected_at: datetime | None = None,
    raw_output: str | object | None = None,
    normalized_output: str | object | None = None,
    sha256: str | object | None = None,
) -> CommandEvidence:
    raw = raw_output if raw_output is not None else f"output:{command}\r\n"
    normalized = (
        normalized_output
        if normalized_output is not None
        else raw.replace("\r\n", "\n").replace("\r", "\n")
    )
    digest = (
        sha256
        if sha256 is not None
        else hashlib.sha256(raw.encode("utf-8")).hexdigest()
    )
    return CommandEvidence(
        execution_id=execution_id if execution_id is not None else uuid4(),
        device_host=DEVICE,
        command=command,
        collected_at=collected_at or datetime.now(timezone.utc),
        raw_output=raw,
        normalized_output=normalized,
        sha256=digest,
    )


def _valid_evidences(*, execution_id: UUID | None = None) -> tuple[CommandEvidence, ...]:
    common_execution_id = execution_id or uuid4()
    return tuple(
        _evidence(command, execution_id=common_execution_id)
        for command in CANONICAL_EVIDENCE_COMMANDS
    )


def test_valid_batch_uses_the_current_authorized_commands():
    evidences = _valid_evidences()

    batch = validate_evidence_batch(evidences)

    assert isinstance(batch, ValidatedEvidenceBatch)
    assert frozenset(CANONICAL_EVIDENCE_COMMANDS) == ALLOWED_COMMANDS
    assert tuple(evidence.command for evidence in batch.evidences) == (
        CANONICAL_EVIDENCE_COMMANDS
    )


def test_out_of_order_batch_is_canonically_ordered_and_preserves_identity():
    evidences = _valid_evidences()
    shuffled = (evidences[2], evidences[0], evidences[3], evidences[1])

    batch = validate_evidence_batch(shuffled)

    for position, command in enumerate(CANONICAL_EVIDENCE_COMMANDS):
        original = next(evidence for evidence in shuffled if evidence.command == command)
        assert batch.evidences[position] is original


def test_input_iterable_is_materialized_only_once():
    evidences = _valid_evidences()

    class SingleUseIterable:
        def __init__(self) -> None:
            self.iterations = 0

        def __iter__(self) -> Iterator[CommandEvidence]:
            self.iterations += 1
            if self.iterations > 1:
                raise AssertionError("iterable reutilizado")
            return iter(evidences)

    source = SingleUseIterable()

    batch = validate_evidence_batch(source)

    assert source.iterations == 1
    assert batch.evidences == evidences


def test_batch_preserves_execution_id_as_uuid():
    execution_id = uuid4()

    batch = validate_evidence_batch(_valid_evidences(execution_id=execution_id))

    assert isinstance(batch.execution_id, UUID)
    assert batch.execution_id is execution_id


def test_batch_and_exposed_collection_are_immutable():
    batch = validate_evidence_batch(_valid_evidences())

    assert isinstance(batch.evidences, tuple)
    with pytest.raises(FrozenInstanceError):
        batch.execution_id = uuid4()
    with pytest.raises(TypeError):
        batch.evidences[0] = batch.evidences[1]


@pytest.mark.parametrize("command", CANONICAL_EVIDENCE_COMMANDS)
def test_evidence_for_returns_the_original_evidence(command):
    evidences = _valid_evidences()
    batch = validate_evidence_batch(reversed(evidences))
    original = next(evidence for evidence in evidences if evidence.command == command)

    assert batch.evidence_for(command) is original


def test_missing_command_is_rejected():
    evidences = _valid_evidences()[:-1]

    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch(evidences)

    assert captured.value.code == "MISSING_COMMAND"


def test_duplicate_command_is_rejected():
    evidences = _valid_evidences()

    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch((*evidences[:-1], evidences[0]))

    assert captured.value.code == "DUPLICATE_COMMAND"


def test_additional_command_is_rejected_without_reflecting_it():
    unknown = "show untrusted-sensitive-value"
    evidences = _valid_evidences()
    altered = (*evidences[:-1], replace(evidences[-1], command=unknown))

    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch(altered)

    assert captured.value.code == "UNAUTHORIZED_COMMAND"
    assert unknown not in str(captured.value)


def test_fewer_than_four_evidences_are_rejected_by_cardinality():
    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch(_valid_evidences()[:2])

    assert captured.value.code == "TOO_FEW_EVIDENCES"


def test_more_than_four_evidences_are_rejected():
    evidences = _valid_evidences()

    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch((*evidences, evidences[0]))

    assert captured.value.code == "TOO_MANY_EVIDENCES"


def test_mismatched_execution_ids_are_rejected():
    evidences = _valid_evidences()
    altered = (*evidences[:-1], replace(evidences[-1], execution_id=uuid4()))

    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch(altered)

    assert captured.value.code == "MISMATCHED_EXECUTION_ID"


def test_non_uuid_execution_id_is_rejected():
    evidences = _valid_evidences()
    altered = (replace(evidences[0], execution_id="invalid"), *evidences[1:])

    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch(altered)

    assert captured.value.code == "INVALID_EXECUTION_ID"


def test_naive_collection_time_is_rejected():
    evidences = _valid_evidences()
    altered = (
        replace(evidences[0], collected_at=datetime(2026, 1, 1)),
        *evidences[1:],
    )

    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch(altered)

    assert captured.value.code == "NAIVE_COLLECTED_AT"


def test_non_utc_collection_time_is_rejected():
    evidences = _valid_evidences()
    non_utc = datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=-4)))
    altered = (replace(evidences[0], collected_at=non_utc), *evidences[1:])

    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch(altered)

    assert captured.value.code == "NON_UTC_COLLECTED_AT"


def test_invalid_timezone_error_is_sanitized_without_exception_chaining():
    sensitive_internal_message = "SENSITIVE_TIMEZONE_INTERNAL_VALUE"

    class BrokenTimezone(tzinfo):
        def utcoffset(self, value):
            raise ValueError(sensitive_internal_message)

        def dst(self, value):
            return None

    evidences = _valid_evidences()
    altered = (
        replace(
            evidences[0],
            collected_at=datetime(2026, 1, 1, tzinfo=BrokenTimezone()),
        ),
        *evidences[1:],
    )

    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch(altered)

    rendered_error = "".join(
        traceback.format_exception(captured.type, captured.value, captured.tb)
    )
    assert captured.value.code == "INVALID_COLLECTED_AT"
    assert sensitive_internal_message not in rendered_error


def test_invalid_sha256_format_is_rejected():
    evidences = _valid_evidences()
    altered = (replace(evidences[0], sha256="invalid"), *evidences[1:])

    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch(altered)

    assert captured.value.code == "INVALID_SHA256_FORMAT"


def test_sha256_mismatch_is_rejected():
    evidences = _valid_evidences()
    altered = (replace(evidences[0], sha256="0" * 64), *evidences[1:])

    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch(altered)

    assert captured.value.code == "SHA256_MISMATCH"


def test_inconsistent_normalized_output_is_rejected():
    evidences = _valid_evidences()
    altered = (
        replace(evidences[0], normalized_output="inconsistent"),
        *evidences[1:],
    )

    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch(altered)

    assert captured.value.code == "NORMALIZED_OUTPUT_MISMATCH"


def test_non_command_evidence_object_is_rejected():
    evidences = _valid_evidences()

    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch((object(), *evidences[1:]))

    assert captured.value.code == "INVALID_EVIDENCE_TYPE"


def test_error_messages_do_not_disclose_evidence_or_device_data():
    sensitive_fragments = (
        "SENSITIVE_RAW_OUTPUT",
        "SENSITIVE_NORMALIZED_OUTPUT",
        "sensitive-device.example.invalid",
        "sensitive-user",
        "sensitive-password",
    )
    sensitive_output = "\n".join(sensitive_fragments)
    evidences = list(_valid_evidences())
    evidences[0] = replace(
        evidences[0],
        device_host=sensitive_fragments[2],
        raw_output=sensitive_output,
        normalized_output=sensitive_output,
        sha256="invalid",
    )

    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch(evidences)

    message = str(captured.value)
    assert all(fragment not in message for fragment in sensitive_fragments)


def test_validation_accepts_current_collector_evidence_semantics():
    execution_id = uuid4()
    raw_outputs = ("alpha\r\n", "beta\r", "gamma\n", "delta")
    evidences = tuple(
        _evidence(command, execution_id=execution_id, raw_output=raw_output)
        for command, raw_output in zip(
            CANONICAL_EVIDENCE_COMMANDS, raw_outputs, strict=True
        )
    )

    batch = validate_evidence_batch(evidences)

    assert batch.execution_id == execution_id
    assert batch.evidences == evidences


def test_validation_does_not_modify_original_evidences():
    evidences = _valid_evidences()
    original_values = tuple(
        (
            evidence.execution_id,
            evidence.command,
            evidence.collected_at,
            evidence.raw_output,
            evidence.normalized_output,
            evidence.sha256,
        )
        for evidence in evidences
    )

    validate_evidence_batch(reversed(evidences))

    assert original_values == tuple(
        (
            evidence.execution_id,
            evidence.command,
            evidence.collected_at,
            evidence.raw_output,
            evidence.normalized_output,
            evidence.sha256,
        )
        for evidence in evidences
    )


def test_service_does_not_import_network_connection_objects():
    import ios_auditor.services.evidence_batch as module

    assert "ConnectHandler" not in module.__dict__
    assert "NetmikoCollector" not in module.__dict__
