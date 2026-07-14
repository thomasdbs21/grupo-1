from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError
from datetime import timedelta, timezone
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)

from ios_auditor.collectors import (
    ALLOWED_COMMANDS,
    CollectorAuthenticationError,
    CollectorConnectionError,
    CollectorTimeoutError,
    CommandNotAllowedError,
    NetmikoCollector,
)


PASSWORD = "CONTRASENA_FICTICIA_NO_REAL"


def _collector(connection: MagicMock) -> tuple[NetmikoCollector, MagicMock]:
    factory = MagicMock(return_value=connection)
    collector = NetmikoCollector(
        host="192.0.2.10",
        port=22,
        username="usuario-prueba",
        password=PASSWORD,
        connection_factory=factory,
    )
    return collector, factory


def test_allowed_commands_are_exactly_the_official_whitelist():
    assert ALLOWED_COMMANDS == frozenset(
        {
            "show running-config",
            "show version",
            "show ip interface brief",
            "show ip ssh",
        }
    )


def test_allowed_command_is_executed_with_cisco_ios_connection():
    connection = MagicMock()
    connection.send_command.return_value = "Cisco IOS XE Software\n"
    collector, factory = _collector(connection)

    evidence = collector.collect("  SHOW VERSION  ")

    factory.assert_called_once_with(
        device_type="cisco_ios",
        host="192.0.2.10",
        port=22,
        username="usuario-prueba",
        password=PASSWORD,
    )
    connection.send_command.assert_called_once_with("show version")
    assert evidence[0].command == "show version"


def test_multiple_commands_use_one_session():
    connection = MagicMock()
    connection.send_command.side_effect = ["version\n", "ssh enabled\n"]
    collector, factory = _collector(connection)

    evidence = collector.collect(["show version", "show ip ssh"])

    factory.assert_called_once()
    assert connection.send_command.call_count == 2
    assert len(evidence) == 2
    assert evidence[0].execution_id == evidence[1].execution_id


def test_forbidden_command_is_rejected_before_connecting():
    collector, factory = _collector(MagicMock())

    with pytest.raises(CommandNotAllowedError, match="no esta autorizado"):
        collector.collect("configure terminal")

    factory.assert_not_called()


@pytest.mark.parametrize(
    "command",
    [
        "show version | include IOS",
        "show version detail",
        "show version; reload",
        "show version\nshow running-config",
        "show ip ssh\rshow version",
    ],
)
def test_command_variants_outside_exact_whitelist_are_rejected(command):
    collector, factory = _collector(MagicMock())

    with pytest.raises(CommandNotAllowedError):
        collector.collect(command)

    factory.assert_not_called()


def test_all_commands_are_validated_before_connection_is_created():
    collector, factory = _collector(MagicMock())

    with pytest.raises(CommandNotAllowedError):
        collector.collect(["show version", "show clock"])

    factory.assert_not_called()


def test_evidence_contains_traceability_and_normalized_output():
    connection = MagicMock()
    raw_output = "Interface              IP-Address\r\nGigabitEthernet1       192.0.2.1\r"
    connection.send_command.return_value = raw_output
    collector, _ = _collector(connection)

    evidence = collector.collect("show ip interface brief")[0]

    assert isinstance(evidence.execution_id, UUID)
    assert evidence.device_host == "192.0.2.10"
    assert evidence.command == "show ip interface brief"
    assert evidence.collected_at.utcoffset() == timedelta(0)
    assert evidence.collected_at.tzinfo is timezone.utc
    assert evidence.raw_output == raw_output
    assert evidence.normalized_output == (
        "Interface              IP-Address\nGigabitEthernet1       192.0.2.1\n"
    )
    assert evidence.sha256 == hashlib.sha256(raw_output.encode("utf-8")).hexdigest()


def test_evidence_is_immutable():
    connection = MagicMock()
    connection.send_command.return_value = "output"
    collector, _ = _collector(connection)
    evidence = collector.collect("show version")[0]

    with pytest.raises(FrozenInstanceError):
        evidence.raw_output = "changed"


def test_command_output_is_not_in_evidence_repr():
    connection = MagicMock()
    connection.send_command.return_value = "SALIDA_SENSIBLE_FICTICIA"
    collector, _ = _collector(connection)

    evidence = collector.collect("show running-config")[0]

    assert "SALIDA_SENSIBLE_FICTICIA" not in repr(evidence)


def test_password_and_username_are_not_in_collector_repr():
    collector, _ = _collector(MagicMock())

    representation = repr(collector)

    assert PASSWORD not in representation
    assert "usuario-prueba" not in representation


def test_session_is_closed_after_success():
    connection = MagicMock()
    connection.send_command.return_value = "output"
    collector, _ = _collector(connection)

    collector.collect("show version")

    connection.disconnect.assert_called_once_with()


def test_session_is_closed_after_command_error():
    connection = MagicMock()
    connection.send_command.side_effect = RuntimeError("fallo simulado")
    collector, _ = _collector(connection)

    with pytest.raises(CollectorConnectionError):
        collector.collect("show version")

    connection.disconnect.assert_called_once_with()


def test_authentication_error_is_converted_to_safe_exception():
    factory = MagicMock(
        side_effect=NetmikoAuthenticationException(
            f"usuario-prueba {PASSWORD} autenticacion rechazada"
        )
    )
    collector = NetmikoCollector(
        "192.0.2.10", 22, "usuario-prueba", PASSWORD, factory
    )

    with pytest.raises(CollectorAuthenticationError) as captured:
        collector.collect("show version")

    message = str(captured.value)
    assert PASSWORD not in message
    assert "usuario-prueba" not in message


def test_timeout_is_converted_to_safe_exception():
    factory = MagicMock(
        side_effect=NetmikoTimeoutException(
            f"timeout usuario-prueba en 192.0.2.10 con {PASSWORD}"
        )
    )
    collector = NetmikoCollector(
        "192.0.2.10", 22, "usuario-prueba", PASSWORD, factory
    )

    with pytest.raises(CollectorTimeoutError) as captured:
        collector.collect("show version")

    message = str(captured.value)
    assert PASSWORD not in message
    assert "usuario-prueba" not in message


def test_configuration_methods_are_never_called():
    connection = MagicMock()
    connection.send_command.return_value = "output"
    collector, _ = _collector(connection)

    collector.collect("show running-config")

    connection.send_config_set.assert_not_called()
    connection.config_mode.assert_not_called()
