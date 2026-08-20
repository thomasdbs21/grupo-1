from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from ios_auditor.domain.models import (
    AnalysisContext,
    InterfaceBriefEntry,
    InterfaceStatus,
    OperationalContext,
    ProtocolStatus,
    RuleStatus,
    ShowIpInterfaceBriefData,
    ShowIpSshData,
)
from ios_auditor.rules import get_interface_operational_rule


def _interface(
    name: str,
    status: InterfaceStatus,
    protocol: ProtocolStatus,
) -> InterfaceBriefEntry:
    return InterfaceBriefEntry(
        name=name,
        ip_address=None,
        method="unset",
        status=status,
        protocol=protocol,
    )


def _context(*interfaces: InterfaceBriefEntry) -> OperationalContext:
    return OperationalContext(
        execution_id=uuid4(),
        device_host="router.example.invalid",
        command="show ip interface brief",
        collected_at=datetime.now(timezone.utc),
        sha256="a" * 64,
        data=ShowIpInterfaceBriefData(interfaces=interfaces),
    )


def test_interface_rule_fails_for_up_down_inconsistency():
    evaluation = get_interface_operational_rule().evaluate(
        _context(_interface("GigabitEthernet2", InterfaceStatus.UP, ProtocolStatus.DOWN))
    )

    assert evaluation.status is RuleStatus.FAIL
    assert evaluation.rule_id == "IOS-IF-001"
    assert evaluation.evidence[0].content == (
        "interface GigabitEthernet2: status up, protocol down"
    )
    assert "router.example.invalid" not in evaluation.evidence[0].content


def test_interface_rule_passes_when_evaluable_interfaces_are_consistent():
    evaluation = get_interface_operational_rule().evaluate(
        _context(
            _interface("GigabitEthernet1", InterfaceStatus.UP, ProtocolStatus.UP),
            _interface("GigabitEthernet2", InterfaceStatus.DOWN, ProtocolStatus.DOWN),
        )
    )

    assert evaluation.status is RuleStatus.PASS
    assert evaluation.evidence == ()


def test_interface_rule_ignores_administratively_down_interfaces():
    evaluation = get_interface_operational_rule().evaluate(
        _context(
            _interface(
                "GigabitEthernet3",
                InterfaceStatus.ADMINISTRATIVELY_DOWN,
                ProtocolStatus.DOWN,
            )
        )
    )

    assert evaluation.status is RuleStatus.NOT_EVALUATED
    assert evaluation.evidence == ()


def test_interface_rule_is_not_evaluated_without_records():
    evaluation = get_interface_operational_rule().evaluate(_context())

    assert evaluation.status is RuleStatus.NOT_EVALUATED


def test_interface_rule_is_not_applicable_to_other_operational_context():
    context = OperationalContext(
        execution_id=uuid4(),
        device_host="router.example.invalid",
        command="show ip ssh",
        collected_at=datetime.now(timezone.utc),
        sha256="b" * 64,
        data=ShowIpSshData(
            enabled=True,
            version="2.0",
            authentication_timeout_seconds=120,
            authentication_retries=3,
        ),
    )

    evaluation = get_interface_operational_rule().evaluate(context)

    assert evaluation.status is RuleStatus.NOT_APPLICABLE


def test_interface_rule_is_not_applicable_to_running_config_context():
    context = AnalysisContext(
        source_path="running.cfg",
        sha256="c" * 64,
        original_content="hostname R1\n",
        normalized_lines=("hostname R1",),
        vty_sections=(),
    )

    evaluation = get_interface_operational_rule().evaluate(context)

    assert evaluation.status is RuleStatus.NOT_APPLICABLE


def test_rule_receives_only_structured_immutable_context():
    context = _context(
        _interface("GigabitEthernet1", InterfaceStatus.UP, ProtocolStatus.UP)
    )

    assert not hasattr(context, "raw_output")
    assert not hasattr(context, "password")
    with pytest.raises(FrozenInstanceError):
        context.command = "changed"
    get_interface_operational_rule().evaluate(context)
