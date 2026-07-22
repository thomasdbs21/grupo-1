from __future__ import annotations

import hashlib
from datetime import timedelta
from unittest.mock import MagicMock, call
from uuid import UUID

import pytest

from ios_auditor.collectors import (
    CollectorConnectionError,
    CommandEvidence,
)
from ios_auditor.domain import FullDeviceAnalysisResult, RuleStatus
from ios_auditor.services import (
    AnalysisError,
    CANONICAL_EVIDENCE_COMMANDS,
    EvidenceBatchValidationError,
    ValidatedEvidenceBatch,
    collect_and_analyze_device,
)
import ios_auditor.services.ssh_analysis as service_module


HOST = "device.example.invalid"
PORT = 22
USERNAME = "<REDACTED>"
PASSWORD = "<REDACTED>"
SENSITIVE_INTERNAL_VALUE = "SENSITIVE_INTERNAL_VALUE_NOT_TO_DISCLOSE"
RUNNING_CONFIG = (
    "line vty 0 4\r\n"
    " transport input ssh\r\n"
    "ip http secure-server\r\n"
)
SHOW_VERSION = "Cisco IOS XE Software, Version 16.09.05\r\n"
SHOW_INTERFACES = (
    "Interface IP-Address OK? Method Status Protocol\r\n"
    "GigabitEthernet1 unassigned YES unset up down\r\n"
)
SHOW_SSH = (
    "SSH Enabled - version 2.0\r\n"
    "Authentication timeout: 120 secs; Authentication retries: 3\r\n"
)
RAW_OUTPUTS = {
    "show running-config": RUNNING_CONFIG,
    "show version": SHOW_VERSION,
    "show ip interface brief": SHOW_INTERFACES,
    "show ip ssh": SHOW_SSH,
}


def _connection() -> MagicMock:
    connection = MagicMock()
    connection.send_command.side_effect = lambda command: RAW_OUTPUTS[command]
    return connection


def _factory(connection: MagicMock) -> MagicMock:
    return MagicMock(return_value=connection)


def _analyze(connection_factory):
    return collect_and_analyze_device(
        host=HOST,
        port=PORT,
        username=USERNAME,
        password=PASSWORD,
        connection_factory=connection_factory,
    )


def test_integral_collection_uses_one_session_and_forwards_one_validated_batch(
    monkeypatch,
):
    connection = _connection()
    factory = _factory(connection)
    validated_batches: list[ValidatedEvidenceBatch] = []
    real_validator = service_module.validate_evidence_batch

    def validate_spy(evidences):
        batch = real_validator(evidences)
        validated_batches.append(batch)
        return batch

    validator = MagicMock(side_effect=validate_spy)
    expected_result = MagicMock(spec=FullDeviceAnalysisResult)
    analyzer = MagicMock(return_value=expected_result)
    monkeypatch.setattr(service_module, "validate_evidence_batch", validator)
    monkeypatch.setattr(
        service_module,
        "analyze_validated_evidence_batch",
        analyzer,
    )

    result = _analyze(factory)

    factory.assert_called_once_with(
        device_type="cisco_ios",
        host=HOST,
        port=PORT,
        username=USERNAME,
        password=PASSWORD,
    )
    assert connection.send_command.call_args_list == [
        call(command) for command in CANONICAL_EVIDENCE_COMMANDS
    ]
    connection.disconnect.assert_called_once_with()
    validator.assert_called_once()
    evidences = validator.call_args.args[0]
    assert isinstance(evidences, tuple)
    assert len(evidences) == 4
    assert all(isinstance(evidence, CommandEvidence) for evidence in evidences)
    assert tuple(evidence.command for evidence in evidences) == (
        CANONICAL_EVIDENCE_COMMANDS
    )
    execution_ids = {evidence.execution_id for evidence in evidences}
    assert len(execution_ids) == 1
    assert isinstance(next(iter(execution_ids)), UUID)
    for evidence in evidences:
        assert evidence.device_host == HOST
        assert evidence.collected_at.utcoffset() == timedelta(0)
        assert evidence.raw_output == RAW_OUTPUTS[evidence.command]
        assert evidence.normalized_output == evidence.raw_output.replace(
            "\r\n", "\n"
        ).replace("\r", "\n")
        assert evidence.sha256 == hashlib.sha256(
            evidence.raw_output.encode("utf-8")
        ).hexdigest()
    analyzer.assert_called_once_with(validated_batches[0])
    assert analyzer.call_args.args[0] is validated_batches[0]
    assert result is expected_result


def test_connection_creation_error_is_sanitized_and_opens_no_partial_flow(
    monkeypatch,
):
    factory = MagicMock(
        side_effect=RuntimeError(
            f"{SENSITIVE_INTERNAL_VALUE} {HOST} {USERNAME} {PASSWORD}"
        )
    )
    validator = MagicMock()
    analyzer = MagicMock()
    monkeypatch.setattr(service_module, "validate_evidence_batch", validator)
    monkeypatch.setattr(
        service_module,
        "analyze_validated_evidence_batch",
        analyzer,
    )

    with pytest.raises(CollectorConnectionError) as captured:
        _analyze(factory)

    message = str(captured.value)
    assert SENSITIVE_INTERNAL_VALUE not in message
    assert HOST not in message
    assert USERNAME not in message
    assert PASSWORD not in message
    validator.assert_not_called()
    analyzer.assert_not_called()


@pytest.mark.parametrize("failure_position", range(4))
def test_each_command_failure_disconnects_without_partial_results(
    failure_position,
    monkeypatch,
):
    connection = MagicMock()
    attempted_commands: list[str] = []

    def send_command(command: str) -> str:
        attempted_commands.append(command)
        if len(attempted_commands) - 1 == failure_position:
            raise RuntimeError(
                f"{SENSITIVE_INTERNAL_VALUE} {HOST} {USERNAME} {PASSWORD}"
            )
        return RAW_OUTPUTS[command]

    connection.send_command.side_effect = send_command
    factory = _factory(connection)
    validator = MagicMock()
    analyzer = MagicMock()
    monkeypatch.setattr(service_module, "validate_evidence_batch", validator)
    monkeypatch.setattr(
        service_module,
        "analyze_validated_evidence_batch",
        analyzer,
    )

    with pytest.raises(CollectorConnectionError) as captured:
        _analyze(factory)

    assert attempted_commands == list(
        CANONICAL_EVIDENCE_COMMANDS[: failure_position + 1]
    )
    factory.assert_called_once()
    connection.disconnect.assert_called_once_with()
    validator.assert_not_called()
    analyzer.assert_not_called()
    message = str(captured.value)
    assert SENSITIVE_INTERNAL_VALUE not in message
    assert HOST not in message
    assert USERNAME not in message
    assert PASSWORD not in message


def test_validation_error_propagates_after_session_is_closed(monkeypatch):
    connection = _connection()
    error = EvidenceBatchValidationError(
        "SYNTHETIC_VALIDATION_ERROR",
        "El lote sintético no es válido.",
    )
    validator = MagicMock(side_effect=error)
    analyzer = MagicMock()
    monkeypatch.setattr(service_module, "validate_evidence_batch", validator)
    monkeypatch.setattr(
        service_module,
        "analyze_validated_evidence_batch",
        analyzer,
    )

    with pytest.raises(EvidenceBatchValidationError) as captured:
        _analyze(_factory(connection))

    assert captured.value is error
    connection.disconnect.assert_called_once_with()
    validator.assert_called_once()
    analyzer.assert_not_called()


def test_incompatible_command_output_disconnects_and_stops_flow(monkeypatch):
    connection = _connection()
    connection.send_command.side_effect = (
        RUNNING_CONFIG,
        object(),
    )
    validator = MagicMock()
    analyzer = MagicMock()
    monkeypatch.setattr(service_module, "validate_evidence_batch", validator)
    monkeypatch.setattr(
        service_module,
        "analyze_validated_evidence_batch",
        analyzer,
    )

    with pytest.raises(CollectorConnectionError) as captured:
        _analyze(_factory(connection))

    assert str(captured.value) == (
        "El dispositivo devolvio una salida SSH no textual."
    )
    assert connection.send_command.call_args_list == [
        call("show running-config"),
        call("show version"),
    ]
    connection.disconnect.assert_called_once_with()
    validator.assert_not_called()
    analyzer.assert_not_called()


def test_analysis_error_propagates_after_session_is_closed(monkeypatch):
    connection = _connection()
    error = AnalysisError("No fue posible completar el análisis integral.")
    analyzer = MagicMock(side_effect=error)
    monkeypatch.setattr(
        service_module,
        "analyze_validated_evidence_batch",
        analyzer,
    )

    with pytest.raises(AnalysisError) as captured:
        _analyze(_factory(connection))

    assert captured.value is error
    connection.disconnect.assert_called_once_with()
    analyzer.assert_called_once()


def test_disconnect_error_uses_existing_safe_policy_and_stops_flow(monkeypatch):
    connection = _connection()
    connection.disconnect.side_effect = RuntimeError(
        f"{SENSITIVE_INTERNAL_VALUE} {HOST} {USERNAME} {PASSWORD}"
    )
    validator = MagicMock()
    analyzer = MagicMock()
    monkeypatch.setattr(service_module, "validate_evidence_batch", validator)
    monkeypatch.setattr(
        service_module,
        "analyze_validated_evidence_batch",
        analyzer,
    )

    with pytest.raises(CollectorConnectionError) as captured:
        _analyze(_factory(connection))

    assert str(captured.value) == (
        "No fue posible cerrar correctamente la sesion SSH."
    )
    connection.disconnect.assert_called_once_with()
    validator.assert_not_called()
    analyzer.assert_not_called()


def test_no_configuration_method_is_used_in_integral_flow(monkeypatch):
    connection = _connection()
    analyzer = MagicMock(return_value=MagicMock(spec=FullDeviceAnalysisResult))
    monkeypatch.setattr(
        service_module,
        "analyze_validated_evidence_batch",
        analyzer,
    )

    _analyze(_factory(connection))

    connection.send_config_set.assert_not_called()
    connection.config_mode.assert_not_called()
    connection.enable.assert_not_called()


def test_complete_simulated_flow_uses_real_validation_parsers_and_rules():
    connection = _connection()
    factory = _factory(connection)

    result = _analyze(factory)

    assert isinstance(result, FullDeviceAnalysisResult)
    assert len(result.evidences) == 4
    assert len({evidence.execution_id for evidence in result.evidences}) == 1
    assert result.execution_id is result.evidences[0].execution_id
    assert len(result.configuration_evaluations) == 3
    assert len(result.operational_results) == 3
    assert len(result.operational_evaluations) == 1
    assert result.operational_evaluations[0].rule_id == "IOS-IF-001"
    assert result.operational_evaluations[0].status is RuleStatus.FAIL
    assert len(result.configuration_findings) == 0
    assert len(result.operational_findings) == 1
    factory.assert_called_once()
    connection.disconnect.assert_called_once_with()
