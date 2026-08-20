from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ios_auditor.domain.models import (
    InterfaceStatus,
    ProtocolStatus,
    ShowIpInterfaceBriefData,
    ShowIpSshData,
    ShowVersionData,
)
from ios_auditor.parsers import (
    SUPPORTED_SHOW_COMMANDS,
    EmptyShowOutputError,
    ShowOutputFormatError,
    UnsupportedShowCommandError,
    parse_show_command,
)


SHOW_VERSION = (
    "Cisco IOS XE Software, Version 16.09.05\r\n"
    "ROUTER-FICTICIO uptime is 1 day, 2 hours, 3 minutes\r\n"
    'System image file is "bootflash:packages.conf"\r\n'
    "cisco CSR1000V (VXE) processor with fictitious memory.\r\n"
    "Processor board ID <REDACTED>\r\n"
)
SHOW_INTERFACES = (
    "Interface              IP-Address      OK? Method Status                Protocol\n"
    "GigabitEthernet1       192.0.2.1       YES manual up                    up\n"
    "GigabitEthernet2       unassigned      YES unset  up                    down\n"
    "GigabitEthernet3       unassigned      YES unset  administratively down down\n"
)
SHOW_SSH = (
    "SSH Enabled - version 2.0\n"
    "Authentication timeout: 120 secs; Authentication retries: 3\n"
)


def test_show_version_is_parsed_without_serial_number():
    result = parse_show_command("show version", SHOW_VERSION)

    assert result == ShowVersionData(
        ios_version="16.09.05",
        platform="CSR1000V",
        software_image="packages.conf",
        uptime="1 day, 2 hours, 3 minutes",
    )
    assert "<REDACTED>" not in repr(result)


def test_show_ip_interface_brief_parses_multiple_interfaces():
    result = parse_show_command("show ip interface brief", SHOW_INTERFACES)

    assert isinstance(result, ShowIpInterfaceBriefData)
    assert len(result.interfaces) == 3
    assert result.interfaces[0].ip_address == "192.0.2.1"
    assert result.interfaces[1].ip_address is None
    assert result.interfaces[1].status is InterfaceStatus.UP
    assert result.interfaces[1].protocol is ProtocolStatus.DOWN
    assert result.interfaces[2].status is InterfaceStatus.ADMINISTRATIVELY_DOWN


def test_interface_status_normalizes_multiple_internal_spaces():
    output = (
        "Interface IP-Address OK? Method Status Protocol\n"
        "GigabitEthernet3 unassigned YES unset administratively   down down\n"
    )

    result = parse_show_command("show ip interface brief", output)

    assert result.interfaces[0].status is InterfaceStatus.ADMINISTRATIVELY_DOWN


def test_unknown_interface_status_rejects_entire_output_safely():
    unknown_line = "GigabitEthernet2 unassigned YES unset testing down"
    output = (
        "Interface IP-Address OK? Method Status Protocol\n"
        "GigabitEthernet1 192.0.2.1 YES manual up up\n"
        f"{unknown_line}\n"
    )

    with pytest.raises(ShowOutputFormatError) as captured:
        parse_show_command("show ip interface brief", output)

    assert unknown_line not in str(captured.value)


def test_show_ip_ssh_is_parsed():
    result = parse_show_command("show ip ssh", SHOW_SSH)

    assert result == ShowIpSshData(
        enabled=True,
        version="2.0",
        authentication_timeout_seconds=120,
        authentication_retries=3,
    )


def test_command_is_normalized_exactly():
    result = parse_show_command("  SHOW IP SSH  ", SHOW_SSH)

    assert isinstance(result, ShowIpSshData)


def test_supported_mapping_is_exact_and_immutable():
    assert set(SUPPORTED_SHOW_COMMANDS) == {
        "show version",
        "show ip interface brief",
        "show ip ssh",
    }
    with pytest.raises(TypeError):
        SUPPORTED_SHOW_COMMANDS["show clock"] = "other.textfsm"


def test_unsupported_command_is_rejected():
    with pytest.raises(UnsupportedShowCommandError, match="no está soportado"):
        parse_show_command("show clock", "12:00:00")


def test_empty_output_is_rejected():
    with pytest.raises(EmptyShowOutputError, match="está vacía"):
        parse_show_command("show version", " \r\n")


def test_unrecognized_output_is_rejected_safely():
    sensitive_output = "SALIDA_FICTICIA_QUE_NO_DEBE_FILTRARSE"

    with pytest.raises(ShowOutputFormatError) as captured:
        parse_show_command("show ip ssh", sensitive_output)

    assert sensitive_output not in str(captured.value)


def test_models_and_interface_collection_are_immutable():
    result = parse_show_command("show ip interface brief", SHOW_INTERFACES)

    assert isinstance(result.interfaces, tuple)
    with pytest.raises(FrozenInstanceError):
        result.interfaces = ()
    with pytest.raises(FrozenInstanceError):
        result.interfaces[0].name = "changed"


def test_parser_module_does_not_import_network_collector():
    import ios_auditor.parsers.show_commands as module

    assert "ConnectHandler" not in module.__dict__
    assert "NetmikoCollector" not in module.__dict__
