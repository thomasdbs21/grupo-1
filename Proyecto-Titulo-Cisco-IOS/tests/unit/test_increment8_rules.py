from __future__ import annotations

import pytest

from ios_auditor.domain import RuleStatus, Severity
from ios_auditor.rules import get_default_registry
from ios_auditor.services.analyzer import load_context_from_bytes


def _context(content: str):
    return load_context_from_bytes(content.encode("utf-8"), source_name="synthetic.cfg")


def _evaluate(rule_id: str, content: str):
    return get_default_registry().get(rule_id).evaluate(_context(content))


def test_ssh_version_1_fails_with_minimal_line_evidence():
    evaluation = _evaluate(
        "IOS-ADM-002",
        "hostname SYNTHETIC\nip ssh version 1\ncrypto key generate rsa\n",
    )

    assert evaluation.status is RuleStatus.FAIL
    assert evaluation.severity is Severity.HIGH
    assert len(evaluation.evidence) == 1
    assert evaluation.evidence[0].content == "ip ssh version 1"
    assert evaluation.evidence[0].line_number == 2
    assert "crypto" not in repr(evaluation.evidence)


def test_ssh_version_2_passes_with_synthetic_evidence():
    evaluation = _evaluate("IOS-ADM-002", " ip ssh version 2  \n")

    assert evaluation.status is RuleStatus.PASS
    assert evaluation.evidence[0].content == "SSH versión 2: configurada"


def test_ssh_without_explicit_version_is_not_evaluated():
    assert _evaluate("IOS-ADM-002", "hostname SYNTHETIC\n").status is RuleStatus.NOT_EVALUATED


def test_negated_ssh_version_does_not_count_as_active():
    assert _evaluate("IOS-ADM-002", "no ip ssh version 1\n").status is RuleStatus.NOT_EVALUATED


def test_ssh_version_requires_exact_tokens():
    assert _evaluate("IOS-ADM-002", "ip ssh version 1 unexpected\n").status is RuleStatus.NOT_EVALUATED


def test_ssh_version_1_precedes_version_2():
    evaluation = _evaluate("IOS-ADM-002", "ip ssh version 2\nip ssh version 1\n")
    assert evaluation.status is RuleStatus.FAIL


@pytest.mark.parametrize(
    "command",
    ("service tcp-small-servers", "service udp-small-servers"),
)
def test_each_small_server_command_fails(command):
    evaluation = _evaluate("IOS-SRV-002", f"{command}\n")
    assert evaluation.status is RuleStatus.FAIL
    assert evaluation.evidence[0].content == command


def test_both_small_server_commands_produce_two_minimal_evidences():
    evaluation = _evaluate(
        "IOS-SRV-002",
        "service tcp-small-servers\nhostname SYNTHETIC\nservice udp-small-servers\n",
    )

    assert evaluation.status is RuleStatus.FAIL
    assert [(item.line_number, item.content) for item in evaluation.evidence] == [
        (1, "service tcp-small-servers"),
        (3, "service udp-small-servers"),
    ]


def test_small_server_optional_arguments_are_preserved():
    evaluation = _evaluate(
        "IOS-SRV-002", "service tcp-small-servers max-servers 10\n"
    )
    assert evaluation.status is RuleStatus.FAIL
    assert evaluation.evidence[0].content == "service tcp-small-servers max-servers 10"


def test_absent_or_negated_small_servers_pass():
    evaluation = _evaluate(
        "IOS-SRV-002",
        "no service tcp-small-servers\nno service udp-small-servers\n",
    )
    assert evaluation.status is RuleStatus.PASS


def test_similar_small_server_text_does_not_match():
    evaluation = _evaluate(
        "IOS-SRV-002", "service tcp-small-servers-extra\nremark service udp-small-servers\n"
    )
    assert evaluation.status is RuleStatus.PASS


@pytest.mark.parametrize(
    "command",
    (
        "ntp server 192.0.2.10",
        "ntp server time.example.invalid prefer",
        "ntp server vrf MANAGEMENT 192.0.2.10 key 7",
        "ntp server ipv6 2001:db8::10 version 4",
    ),
)
def test_valid_ntp_server_variants_pass_without_disclosing_destination(command):
    evaluation = _evaluate("IOS-NTP-001", f"{command}\n")

    assert evaluation.status is RuleStatus.PASS
    assert evaluation.evidence[0].content == "servidor NTP: configurado"
    assert not any(token in evaluation.evidence[0].content for token in command.split()[2:])


def test_multiple_ntp_servers_pass_with_single_synthetic_evidence():
    evaluation = _evaluate(
        "IOS-NTP-001",
        "ntp server 192.0.2.10\nntp server time.example.invalid\n",
    )
    assert evaluation.status is RuleStatus.PASS
    assert len(evaluation.evidence) == 1


@pytest.mark.parametrize(
    "content",
    (
        "hostname SYNTHETIC\n",
        "no ntp server 192.0.2.10\n",
        "ntp server\n",
        "ntp server prefer\n",
        "ntp server vrf ONLY_NAME\n",
    ),
)
def test_absent_negated_or_incomplete_ntp_server_fails(content):
    evaluation = _evaluate("IOS-NTP-001", content)
    assert evaluation.status is RuleStatus.FAIL
    assert evaluation.evidence[0].content == "servidor NTP: no configurado"


@pytest.mark.parametrize(
    "command",
    (
        "logging host 192.0.2.20",
        "logging host logs.example.invalid",
        "logging host 192.0.2.20 transport udp port 514",
        "logging host 192.0.2.20 vrf MANAGEMENT",
        "logging 192.0.2.20",
        "logging logs.example.invalid",
    ),
)
def test_supported_syslog_destinations_pass_with_synthetic_evidence(command):
    evaluation = _evaluate("IOS-LOG-001", f"{command}\n")

    assert evaluation.status is RuleStatus.PASS
    assert evaluation.evidence[0].content == "servidor Syslog remoto: configurado"
    assert not any(token in evaluation.evidence[0].content for token in command.split()[1:])


def test_multiple_syslog_destinations_still_return_one_synthetic_evidence():
    evaluation = _evaluate(
        "IOS-LOG-001",
        "logging host 192.0.2.20\nlogging logs.example.invalid\n",
    )
    assert evaluation.status is RuleStatus.PASS
    assert len(evaluation.evidence) == 1


@pytest.mark.parametrize(
    "keyword",
    (
        "buffered",
        "console",
        "monitor",
        "trap",
        "source-interface",
        "facility",
        "history",
        "origin-id",
        "discriminator",
        "persistent",
        "rate-limit",
        "filter",
        "synchronous",
        "queue-limit",
    ),
)
def test_local_logging_directives_do_not_count_as_destinations(keyword):
    evaluation = _evaluate("IOS-LOG-001", f"logging {keyword} synthetic-value\n")
    assert evaluation.status is RuleStatus.FAIL


def test_absent_or_negated_syslog_destination_fails_with_exact_evidence():
    evaluation = _evaluate(
        "IOS-LOG-001", "no logging host 192.0.2.20\nlogging buffered 4096\n"
    )
    assert evaluation.status is RuleStatus.FAIL
    assert evaluation.evidence[0].content == "servidor Syslog remoto: no configurado"


@pytest.mark.parametrize(
    "command",
    (
        "logging host",
        "logging host 192.0.2.20 unknown-option value",
        "logging unknown-single-token",
        "logging destination-group synthetic-value",
    ),
)
def test_potential_remote_unknown_syslog_syntax_is_not_evaluated(command):
    evaluation = _evaluate("IOS-LOG-001", f"{command}\n")
    assert evaluation.status is RuleStatus.NOT_EVALUATED
    assert evaluation.evidence == ()
