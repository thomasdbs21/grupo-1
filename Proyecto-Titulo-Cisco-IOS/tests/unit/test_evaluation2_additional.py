"""Contratos conservadores de las tres reglas, sin red ni secretos reales."""

from dataclasses import FrozenInstanceError, replace
from unittest.mock import Mock
import socket

import paramiko
import pytest

from ios_auditor.domain import RuleStatus
from ios_auditor.rules import get_default_registry
from ios_auditor.rules.evaluation2_operational import get_expanded_operational_rules
from ios_auditor.services.analyzer import load_context_from_bytes, _evaluate_rule
from ios_auditor.services.rule_results import findings_from_evaluations
from test_operational_expansion import context, check, outputs

PASS, FAIL, NA, NE = (RuleStatus.PASS, RuleStatus.FAIL,
                      RuleStatus.NOT_APPLICABLE, RuleStatus.NOT_EVALUATED)
MARKER = "SYNTHETIC_SECRET_MARKER"


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Este contrato se prueba exclusivamente offline.")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(paramiko.SSHClient, "connect", forbidden)


def static_check(rule_id, config, expected):
    rule = get_default_registry().get(rule_id)
    ctx = load_context_from_bytes(config.encode(), source_name="synthetic-config")
    before = repr(ctx)
    evaluation = _evaluate_rule(rule, ctx)
    assert evaluation.status == expected
    assert repr(ctx) == before
    assert bool(findings_from_evaluations((evaluation,))) == (expected == FAIL)
    assert evaluation.evidence[0].sha256 == ctx.sha256
    assert evaluation.evidence[0].content == evaluation.message
    assert evaluation.evidence[0].line_number is None
    for value in (MARKER, "identity-marker", "192.0.2."):
        assert value not in repr(evaluation)
    return evaluation


@pytest.mark.parametrize("directive,expected", [
    (f"username identity-marker password {MARKER}", FAIL),
    (f"username identity-marker password 0 {MARKER}", FAIL),
    (f"username identity-marker password 7 {MARKER}", FAIL),
    (f"username identity-marker privilege 15 password 7 {MARKER}", FAIL),
    (f"username identity-marker secret {MARKER}", PASS),
    *[(f"username identity-marker secret {kind} {MARKER}", PASS) for kind in (0, 5, 8, 9)],
    (f"username identity-marker privilege 0 secret 9 {MARKER}", PASS),
    ("hostname synthetic", NA),
    ("no username identity-marker", NA),
    ("username", NE), ("username identity-marker", NE),
    ("username identity-marker password", NE),
    ("username identity-marker password 7", NE),
    ("username identity-marker secret 9", NE),
    (f"username identity-marker secret 7 {MARKER}", NE),
    (f"username identity-marker password 9 {MARKER}", NE),
    (f"username identity-marker privilege 16 secret {MARKER}", NE),
    (f"username identity-marker algorithm-type scrypt secret {MARKER}", NE),
    ("username identity-marker nopassword", NE),
    (f"username identity-marker password {MARKER} secret {MARKER}", NE),
    (f"username identity-marker secret {MARKER} password {MARKER}", NE),
    (f'username "identity-marker" secret {MARKER}', NE),
    (f"banner motd #\nusername identity-marker password {MARKER}\n#\nhostname synthetic", NA),
    (f"! username identity-marker password {MARKER}\nhostname synthetic", NA),
    (f"crypto pki trustpoint SYNTHETIC\n username identity-marker password {MARKER}", NA),
    (f"username identity-marker secret {MARKER}\n unexpected child", NE),
])
def test_local_user_explicit_supported_syntax(directive, expected):
    static_check("IOS-AUTH-003", directive + "\n", expected)


@pytest.mark.parametrize("first,second", [("password", "secret"), ("secret", "password"),
                                         ("secret", "secret"), ("password", "password")])
def test_same_identity_never_guesses_effective_precedence(first, second):
    cfg = f"username identity-marker {first} {MARKER}\nusername identity-marker {second} {MARKER}\n"
    static_check("IOS-AUTH-003", cfg, NE)


def test_supported_failed_other_identity_is_not_hidden_by_ambiguity():
    cfg = f"username identity-marker secret {MARKER}\nusername identity-marker password {MARKER}\n"
    cfg += f"username second-marker password {MARKER}\n"
    static_check("IOS-AUTH-003", cfg, FAIL)


@pytest.mark.parametrize("header,directive,expected", [
    ("line console 0", "exec-timeout 0 0", FAIL),
    ("line vty 0 4", "exec-timeout 0 0", FAIL),
    ("line vty 5 15", "exec-timeout 0", FAIL),
    ("line vty 0 4", "exec-timeout 0 1", PASS),
    ("line console 0", "exec-timeout 1", PASS),
    ("line console 0", "exec-timeout 30 0", PASS),
    ("line vty 0 4", "", NE),
    ("line console 0", "no exec-timeout", NE),
    ("line console 0", "default exec-timeout", NE),
    ("line console 0", "exec-timeout -1 0", NE),
    ("line console 0", "exec-timeout 0 0 extra", NE),
    ("line console 0", "exec-timeout unknown", NE),
    ("line console 0", "exec-timeout", NE),
    ("line console 0", "exec-timeout 0 0\n exec-timeout 1 0", NE),
    ("line console 0", "exec-timeout 0 0\n no exec-timeout", NE),
    ("line vty 4 0", "exec-timeout 0 0", NE),
    ("line vty unknown", "exec-timeout 0 0", NE),
    ("line console 0 1", "exec-timeout 0 0", NE),
    ("line aux 0", "exec-timeout 0 0", NA),
    ("interface GigabitEthernet1", "exec-timeout 0 0", NA),
])
def test_timeout_without_invented_duration_policy(header, directive, expected):
    static_check("IOS-ADM-003", header + "\n " + directive + "\n", expected)


def test_timeout_overlapping_or_duplicate_sections_are_ambiguous():
    for header in ("line vty 0 4", "line vty 2 6"):
        static_check("IOS-ADM-003", "line vty 0 4\n exec-timeout 0 0\n" + header + "\n exec-timeout 1 0\n", NE)


def test_explicit_disabled_timeout_elsewhere_dominates_absent_timeout():
    static_check("IOS-ADM-003", "line console 0\n login local\nline vty 0 4\n exec-timeout 0 0\n", FAIL)


def interface_raw(name="GigabitEthernet1", state="down", protocol="down", packets=0, errors=0):
    return (f"{name} is {state}, line protocol is {protocol}\n"
            f"  {packets} packets input, 0 bytes, 0 no buffer\n"
            f"  {errors} input errors, 0 CRC\n"
            f"  {packets} packets output, 0 bytes\n"
            f"  {errors} output errors, 0 collisions\n")


@pytest.mark.parametrize("children,state,protocol,packets,expected", [
    ("description NETAUDIT_UNUSED\n no shutdown", "down", "down", 0, FAIL),
    ("description NETAUDIT_UNUSED\n shutdown", "administratively down", "down", 0, PASS),
    ("description NETAUDIT_UNUSED\n no shutdown", "up", "up", 20000, PASS),
    ("no shutdown", "down", "down", 0, NE),
    ("description no utilizada\n no shutdown", "down", "down", 0, NE),
    ("description NETAUDIT_UNUSED", "down", "down", 0, NE),
    ("description NETAUDIT_UNUSED\n no shutdown", "down", "down", 1, NE),
    ("description NETAUDIT_UNUSED\n no shutdown", "up", "down", 0, NE),
    ("shutdown", "down", "down", 0, NE),
    ("shutdown", "up", "up", 20000, NE),
    ("no shutdown", "administratively down", "down", 0, NE),
    ("description NETAUDIT_UNUSED\n shutdown\n no shutdown", "down", "down", 0, NE),
    ("description NETAUDIT_UNUSED\n description other\n no shutdown", "down", "down", 0, NE),
])
def test_unused_interface_requires_declared_intent_and_corroboration(children, state, protocol, packets, expected):
    cfg = "interface GigabitEthernet1\n " + children + "\n"
    check("IOS-INT-001", cfg, {"show interfaces": interface_raw(state=state, protocol=protocol, packets=packets)}, expected)


@pytest.mark.parametrize("name,expected", [("Loopback0", NA), ("Tunnel1", NA), ("Vlan1", NA),
                                         ("Port-channel1", NA), ("GigabitEthernet1.10", NA),
                                         ("Unknown1", NE), ("Gi1", NE), ("GigabitEthernet1.bad", NE)])
def test_excluded_or_unknown_interface_types(name, expected):
    check("IOS-INT-001", f"interface {name}\n description NETAUDIT_UNUSED\n no shutdown\n",
          {"show interfaces": interface_raw(name)}, expected)


@pytest.mark.parametrize("config,raw", [
    ("hostname synthetic\n", interface_raw()),
    ("interface GigabitEthernet1\n", "UNKNOWN_FORMAT\n"),
    ("interface GigabitEthernet1\n", ""),
    ("interface GigabitEthernet1\n", interface_raw() + interface_raw()),
    ("interface GigabitEthernet1\ninterface GigabitEthernet1\n", interface_raw()),
    ("interface GigabitEthernet1\ninterface GigabitEthernet2\n", interface_raw()),
    ("interface GigabitEthernet1\n description NETAUDIT_UNUSED\n no shutdown\n", interface_raw(errors=1)),
    ("interface GigabitEthernet1\n description NETAUDIT_UNUSED\n no shutdown\n",
     "GigabitEthernet1 is down, line protocol is down\n"),
])
def test_uncorrelatable_or_insufficient_interface_evidence(config, raw):
    check("IOS-INT-001", config, {"show interfaces": raw}, NE)


def test_unused_interface_missing_source_and_fail_with_another_unknown():
    check("IOS-INT-001", "interface GigabitEthernet1\n", {}, NE)
    cfg = "interface GigabitEthernet1\n description NETAUDIT_UNUSED\n no shutdown\ninterface GigabitEthernet2\n"
    check("IOS-INT-001", cfg, {"show interfaces": interface_raw() + interface_raw("GigabitEthernet2")}, FAIL)


@pytest.mark.parametrize("rule_id", ["IOS-AUTH-003", "IOS-ADM-003", "IOS-INT-001"])
def test_metadata_immutable_sources_and_safe_internal_error(rule_id, monkeypatch, capsys, caplog):
    rule = (get_default_registry().get(rule_id) if rule_id != "IOS-INT-001" else
            next(item for item in get_expanded_operational_rules() if item.metadata.id == rule_id))
    assert rule.metadata.version == "1.0.0" and rule.metadata.enabled
    assert rule.metadata.references and rule.metadata.false_positives and rule.metadata.exceptions
    assert all(url.startswith("https://www.cisco.com/") for url in rule.metadata.references)
    assert rule.metadata.required_sources == (("running-config", "show interfaces")
                                              if rule_id == "IOS-INT-001" else ("running-config",))
    with pytest.raises(FrozenInstanceError):
        rule.metadata = replace(rule.metadata, enabled=False)
    def broken(self, _):
        raise RuntimeError(MARKER)
    monkeypatch.setattr(type(rule), "evaluate", broken)
    ctx = context("hostname synthetic\n", {}) if rule_id == "IOS-INT-001" else load_context_from_bytes(b"hostname synthetic\n", source_name="synthetic-config")
    evaluation = _evaluate_rule(rule, ctx)
    assert evaluation.status == RuleStatus.ERROR
    assert not findings_from_evaluations((evaluation,))
    captured = capsys.readouterr()
    assert MARKER not in repr(evaluation) + caplog.text + captured.out + captured.err


@pytest.mark.parametrize("scenario", ["seguro", "inseguro", "no_evaluable"])
def test_previous_eighteen_rule_states_are_preserved(scenario):
    from ios_auditor.services import collect_and_analyze_device
    connection = Mock()
    connection.send_command.side_effect = outputs(scenario).__getitem__
    result = collect_and_analyze_device(host="synthetic.example.invalid", port=22,
                                       username="<REDACTED>", password="<REDACTED>",
                                       connection_factory=Mock(return_value=connection))
    expected = {
        "seguro": [PASS] * 18,
        "inseguro": [FAIL] * 5 + [PASS] * 2 + [FAIL] * 5 + [PASS] + [FAIL] * 4 + [NE],
        "no_evaluable": [PASS] * 3 + [NE] + [PASS] * 3 + [NE] * 4 + [PASS] * 2 + [NE] * 5,
    }
    old = [item.status for item in result.evaluations if item.rule_id not in {"IOS-AUTH-003", "IOS-ADM-003", "IOS-INT-001"}]
    assert old == expected[scenario]
    assert len(result.evaluations) == len({item.rule_id for item in result.evaluations}) == 21


@pytest.mark.parametrize("rule_id", ["IOS-AUTH-003", "IOS-ADM-003"])
def test_each_static_addition_can_be_disabled_without_finding(rule_id):
    from ios_auditor.rules.registry import build_registry
    from ios_auditor.services.analyzer import analyze_bytes
    metadata = tuple(replace(rule.metadata, enabled=False) if rule.metadata.id == rule_id else rule.metadata
                     for rule in get_default_registry().list_rules())
    registry = build_registry(metadata)
    result = analyze_bytes(outputs("inseguro")["show running-config"].encode(),
                           source_name="synthetic-config", registry=registry)
    assert len(result.evaluations) == 13
    assert rule_id not in {item.rule_id for item in result.evaluations + result.findings}


def test_multisource_addition_registry_disabling_is_dynamic(monkeypatch):
    from ios_auditor.rules.registry import build_registry
    import ios_auditor.services.full_device_analysis as service
    from ios_auditor.services import collect_and_analyze_device
    rules = get_expanded_operational_rules()
    metadata = tuple(replace(rule.metadata, enabled=False) if rule.metadata.id == "IOS-INT-001" else rule.metadata
                     for rule in rules)
    selected = build_registry(metadata, tuple(type(rule) for rule in rules)).list_rules(enabled_only=True)
    monkeypatch.setattr(service, "get_expanded_operational_rules", lambda: selected)
    connection = Mock()
    connection.send_command.side_effect = outputs("inseguro").__getitem__
    result = collect_and_analyze_device(host="synthetic.example.invalid", port=22,
                                       username="<REDACTED>", password="<REDACTED>",
                                       connection_factory=Mock(return_value=connection))
    assert len(result.evaluations) == 20
    assert "IOS-INT-001" not in {item.rule_id for item in result.evaluations + result.findings}
    connection.disconnect.assert_called_once_with()
