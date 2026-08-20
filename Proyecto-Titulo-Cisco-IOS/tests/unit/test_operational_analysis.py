from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from ios_auditor.collectors import CommandEvidence
from ios_auditor.domain.models import OperationalContext, ShowIpSshData
from ios_auditor.services import (
    OperationalAnalysisError,
    OperationalEvidenceError,
    parse_collected_show_evidence,
)


RAW_OUTPUT = (
    "SSH Enabled - version 2.0\r\n"
    "Authentication timeout: 120 secs; Authentication retries: 3\r\n"
)
NORMALIZED_OUTPUT = RAW_OUTPUT.replace("\r\n", "\n")
DEVICE = "router.example.invalid"


def _evidence(
    *,
    raw_output: str = RAW_OUTPUT,
    normalized_output: str | None = None,
    sha256: str | None = None,
    command: str = "show ip ssh",
    execution_id: UUID | None = None,
    collected_at: datetime | None = None,
) -> CommandEvidence:
    return CommandEvidence(
        execution_id=execution_id or uuid4(),
        device_host=DEVICE,
        command=command,
        collected_at=collected_at or datetime.now(timezone.utc),
        raw_output=raw_output,
        normalized_output=(
            normalized_output
            if normalized_output is not None
            else raw_output.replace("\r\n", "\n").replace("\r", "\n")
        ),
        sha256=sha256 or hashlib.sha256(raw_output.encode("utf-8")).hexdigest(),
    )


def test_service_builds_context_and_preserves_traceability():
    execution_id = uuid4()
    collected_at = datetime.now(timezone.utc)
    evidence = _evidence(execution_id=execution_id, collected_at=collected_at)

    context = parse_collected_show_evidence(evidence)

    assert isinstance(context, OperationalContext)
    assert isinstance(context.data, ShowIpSshData)
    assert context.execution_id == execution_id
    assert context.device_host == DEVICE
    assert context.command == "show ip ssh"
    assert context.collected_at is collected_at
    assert context.collected_at.utcoffset() == timedelta(0)
    assert context.sha256 == evidence.sha256
    assert not hasattr(context, "raw_output")


def test_service_normalizes_evidence_command():
    context = parse_collected_show_evidence(_evidence(command="  SHOW IP SSH  "))

    assert context.command == "show ip ssh"


def test_altered_sha256_is_rejected():
    with pytest.raises(OperationalEvidenceError, match="integridad"):
        parse_collected_show_evidence(_evidence(sha256="0" * 64))


def test_inconsistent_normalized_output_is_rejected():
    with pytest.raises(OperationalEvidenceError, match="normalizada"):
        parse_collected_show_evidence(
            _evidence(normalized_output="SALIDA_NORMALIZADA_INCONSISTENTE")
        )


def test_non_utc_collection_time_is_rejected():
    non_utc = datetime.now(timezone(timedelta(hours=-4)))

    with pytest.raises(OperationalEvidenceError, match="UTC"):
        parse_collected_show_evidence(_evidence(collected_at=non_utc))


def test_unsupported_evidence_command_is_rejected():
    with pytest.raises(OperationalEvidenceError, match="no está soportado"):
        parse_collected_show_evidence(_evidence(command="show running-config"))


def test_parser_error_is_translated_without_output_disclosure():
    sensitive_output = "SALIDA_FICTICIA_SENSIBLE_NO_REVELAR"
    evidence = _evidence(raw_output=sensitive_output)

    with pytest.raises(OperationalAnalysisError) as captured:
        parse_collected_show_evidence(evidence)

    assert sensitive_output not in str(captured.value)
    assert DEVICE not in str(captured.value)


def test_operational_context_is_immutable():
    context = parse_collected_show_evidence(_evidence())

    with pytest.raises(FrozenInstanceError):
        context.device_host = "changed"


def test_service_does_not_receive_or_open_connections():
    import ios_auditor.services.operational_analysis as module

    assert "ConnectHandler" not in module.__dict__
    assert "NetmikoCollector" not in module.__dict__
