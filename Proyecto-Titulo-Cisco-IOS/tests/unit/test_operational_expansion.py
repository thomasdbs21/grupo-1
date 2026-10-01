"""Contratos operacionales nuevos; toda recopilación es simulada u offline."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import socket
from unittest.mock import Mock
from uuid import uuid4

import paramiko
import pytest

from ios_auditor.collectors import ALLOWED_COMMANDS, CommandEvidence, NetmikoCollector, CommandNotAllowedError
from ios_auditor.domain.models import MultiSourceContext, OperationalContext, RuleStatus
from ios_auditor.parsers import parse_show_command
from ios_auditor.rules.evaluation2_operational import get_expanded_operational_rules, _counter_direction
from ios_auditor.services import (CANONICAL_EVIDENCE_COMMANDS, collect_and_analyze_device,
                                 validate_evidence_batch, analyze_validated_evidence_batch)
from ios_auditor.services.analyzer import load_context_from_bytes, _evaluate_rule
from ios_auditor.services.rule_results import findings_from_evaluations
from ios_auditor.api.full_device_serialization import to_full_device_analysis_response

ROOT = Path(__file__).resolve().parents[2]
COMMANDS = ("show interfaces", "show access-lists", "show ntp associations", "show ip ospf neighbor")
IDS = ("IOS-INT-002", "IOS-ACL-002", "IOS-NTP-002", "IOS-AVL-001", "IOS-OSPF-002", "IOS-INT-001")
PASS, FAIL, NA, NE = (RuleStatus.PASS, RuleStatus.FAIL,
                      RuleStatus.NOT_APPLICABLE, RuleStatus.NOT_EVALUATED)
NTP_HEADER = "address ref clock st when poll reach delay offset disp\n"
OSPF_HEADER = "Neighbor ID Pri State Dead Time Address Interface\n"


@pytest.fixture(autouse=True)
def block_real_connections(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("La expansión debe comprobarse sin conexiones reales.")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(paramiko.SSHClient, "connect", forbidden)


def fixture_output(command, scenario="seguro"):
    filename = command.replace(" ", "_").replace("-", "_") + ".txt"
    return (ROOT / "samples/evaluacion_2/operacional" / scenario / filename).read_text(encoding="utf-8")


def outputs(scenario="seguro"):
    return {
        "show running-config": (ROOT / "samples/evaluacion_2" / f"escenario_{scenario}.cfg").read_text(encoding="utf-8"),
        "show version": "Cisco IOS XE Software, Version 16.09.05\n",
        "show ip ssh": "SSH Enabled - version 2.0\n",
        **{command: fixture_output(command, scenario) for command in CANONICAL_EVIDENCE_COMMANDS
           if command not in {"show running-config", "show version", "show ip ssh"}},
    }


def context(configuration, values):
    config = load_context_from_bytes(configuration.encode(), source_name="synthetic-config")
    execution_id = uuid4()
    timestamp = datetime.now(timezone.utc)
    operational = tuple(OperationalContext(execution_id, "synthetic.example.invalid", command,
                                          timestamp, hashlib.sha256(raw.encode()).hexdigest(),
                                          parse_show_command(command, raw))
                        for command, raw in values.items())
    return MultiSourceContext(config, operational)


def check(rule_id, configuration, values, expected):
    rule = next(item for item in get_expanded_operational_rules() if item.metadata.id == rule_id)
    ctx = context(configuration, values)
    before = repr(ctx)
    evaluation = _evaluate_rule(rule, ctx)
    assert evaluation.status == expected
    assert repr(ctx) == before
    assert len(findings_from_evaluations((evaluation,))) == (expected == FAIL)
    assert evaluation.evidence or not values
    for evidence in evaluation.evidence:
        assert evidence.content == evaluation.message
        assert len(evidence.sha256) == 64
    for marker in ("192.0.2.", "GigabitEthernet1", "ACL-SINTETICA", "SECRET_MARKER"):
        assert marker not in repr(evaluation)
    return evaluation


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("scenario,recognized", [("seguro", True), ("inseguro", True), ("no_evaluable", False)])
def test_parsers_recognize_only_supported_fixtures(command, scenario, recognized):
    data = parse_show_command(command, fixture_output(command, scenario))
    assert data.recognized == recognized
    with pytest.raises(FrozenInstanceError):
        data.recognized = not recognized


@pytest.mark.parametrize("command", COMMANDS)
def test_unknown_output_is_not_an_empty_known_table(command):
    data = parse_show_command(command, "SECRET_MARKER unknown output\n")
    assert not data.recognized
    assert "SECRET_MARKER" not in repr(data)


@pytest.mark.parametrize("command", COMMANDS)
def test_empty_output_contract(command):
    data = parse_show_command(command, "")
    assert data.recognized == (command == "show access-lists")


def test_ntp_and_ospf_addresses_are_discarded():
    ntp = parse_show_command("show ntp associations", fixture_output("show ntp associations"))
    ospf = parse_show_command("show ip ospf neighbor", fixture_output("show ip ospf neighbor"))
    assert ntp.associations[0].synchronized
    assert ntp.associations[0].reach == 255
    assert ospf.neighbors[0].state == "FULL"
    assert "192.0.2." not in repr(ntp) + repr(ospf)


@pytest.mark.parametrize("config,brief,status", [
    ("interface GigabitEthernet1\n description Documentado\n", "up up", PASS),
    ("interface GigabitEthernet1\n no description\n", "up up", FAIL),
    ("interface GigabitEthernet1\n description\n", "up up", NE),
    ("hostname R1\n", "up up", NE),
    ("interface GigabitEthernet1\n description A\ninterface GigabitEthernet1\n description B\n", "up up", NE),
    ("hostname R1\n", "down down", NA),
    ("hostname R1\n", "administratively down down", NA),
])
def test_interface_descriptions(config, brief, status):
    raw = "Interface IP-Address OK? Method Status Protocol\nGigabitEthernet1 192.0.2.1 YES manual " + brief + "\n"
    check("IOS-INT-002", config, {"show ip interface brief": raw}, status)


@pytest.mark.parametrize("suffix,show,status", [
    ("interface GigabitEthernet1\n ip access-group ACL-SINTETICA in\n", "valid", PASS),
    ("interface GigabitEthernet1\n ip access-group ACL-SINTETICA out\n", "valid", PASS),
    ("", "valid", FAIL),
    ("line vty 0 4\n access-class ACL-SINTETICA in\n", "valid", NE),
    ("ntp access-group peer ACL-SINTETICA\n", "valid", NE),
    ("route-map SYNTHETIC permit 10\n match ip address ACL-SINTETICA\n", "valid", NE),
    ("snmp-server community SECRET_MARKER RO ACL-SINTETICA\n", "valid", NE),
    ("interface GigabitEthernet1\n ip access-group ACL-SINTETICA sideways\n", "valid", NE),
    ("", "", NE),
    ("", "SECRET_MARKER unsupported", NE),
])
def test_acl_application(suffix, show, status):
    cfg = "ip access-list extended ACL-SINTETICA\n deny ip any any\n" + suffix
    raw = fixture_output("show access-lists") if show == "valid" else show
    check("IOS-ACL-002", cfg, {"show access-lists": raw}, status)


def test_acl_absence_and_show_conflict():
    check("IOS-ACL-002", "hostname R1\n", {"show access-lists": ""}, NA)
    check("IOS-ACL-002", "hostname R1\n", {"show access-lists": fixture_output("show access-lists")}, NE)


@pytest.mark.parametrize("marker,stratum,reach,status", [
    ("*~", 2, "377", PASS), ("~", 2, "377", FAIL), ("+", 2, "377", FAIL),
    ("*~", 16, "377", FAIL), ("*~", 2, "0", FAIL), ("~", 17, "377", NE),
    ("~", 2, "777", NE),
])
def test_ntp(marker, stratum, reach, status):
    raw = NTP_HEADER + f"{marker}192.0.2.10 192.0.2.11 {stratum} 10 64 {reach} 1.0 0.0 0.1\n"
    check("IOS-NTP-002", "hostname R1\n", {"show ntp associations": raw}, status)


def test_ntp_empty_table_and_partial_table():
    check("IOS-NTP-002", "hostname R1\n", {"show ntp associations": NTP_HEADER}, NA)
    check("IOS-NTP-002", "hostname R1\n", {"show ntp associations": NTP_HEADER + "*~192.0.2.10 incomplete\n"}, NE)


@pytest.mark.parametrize("packets,errors,status", [
    (20000, 0, PASS), (9900, 100, PASS), (9899, 101, FAIL), (20000, 500, FAIL),
    (50, 1, NE), (None, 500, NE), (20000, None, NE), (9999, 0, NE), (-1, 1, NE),
])
def test_availability_threshold_boundaries(packets, errors, status):
    assert _counter_direction(packets, errors) == status


@pytest.mark.parametrize("scenario,status", [("seguro", PASS), ("inseguro", FAIL), ("no_evaluable", NE)])
def test_availability_rule(scenario, status):
    check("IOS-AVL-001", "hostname R1\n", {"show interfaces": fixture_output("show interfaces", scenario)}, status)


def test_availability_inactive_or_missing_counters():
    check("IOS-AVL-001", "hostname R1\n", {"show interfaces": "GigabitEthernet1 is down, line protocol is down\n"}, NA)
    check("IOS-AVL-001", "hostname R1\n", {"show interfaces": "GigabitEthernet1 is up, line protocol is up\n"}, NE)


@pytest.mark.parametrize("state,status", [("FULL/DR", PASS), ("FULL/-", PASS), ("2WAY/DROTHER", PASS),
                                        ("2WAY/DR", NE), ("INIT/DROTHER", NE), ("EXSTART/DR", NE), ("DOWN/-", NE)])
def test_ospf_no_invented_failed_expectations(state, status):
    raw = OSPF_HEADER + f"192.0.2.2 1 {state} 00:00:30 192.0.2.2 GigabitEthernet1\n"
    evaluation = check("IOS-OSPF-002", "router ospf 1\n", {"show ip ospf neighbor": raw}, status)
    assert evaluation.status != FAIL


def test_ospf_empty_and_unknown():
    check("IOS-OSPF-002", "hostname R1\n", {"show ip ospf neighbor": OSPF_HEADER}, NA)
    check("IOS-OSPF-002", "router ospf 1\n", {"show ip ospf neighbor": OSPF_HEADER}, NE)
    check("IOS-OSPF-002", "router ospf 1\n", {"show ip ospf neighbor": "SECRET_MARKER unknown\n"}, NE)


@pytest.mark.parametrize("rule_id", IDS)
def test_missing_sources_and_safe_internal_errors(rule_id, monkeypatch):
    rule = next(item for item in get_expanded_operational_rules() if item.metadata.id == rule_id)
    assert rule.metadata.enabled and rule.metadata.version == "1.0.0"
    assert rule.metadata.references and rule.metadata.risk and rule.metadata.exceptions
    evaluation = check(rule_id, "hostname R1\n", {}, NE)
    assert not findings_from_evaluations((evaluation,))
    import ios_auditor.rules.evaluation2_operational as module
    def broken(_):
        raise RuntimeError("SECRET_MARKER")
    monkeypatch.setitem(module._CHECKS, rule_id, broken)
    ctx = context("hostname R1\n", {})
    error = _evaluate_rule(rule, ctx)
    assert error.status == RuleStatus.ERROR
    assert "SECRET_MARKER" not in repr(error)
    assert not findings_from_evaluations((error,))


@pytest.mark.parametrize("scenario,findings", [("seguro", 0), ("inseguro", 17), ("no_evaluable", 0)])
def test_full_eight_command_flow_one_simulated_session(scenario, findings):
    raw = outputs(scenario)
    connection = Mock()
    connection.send_command.side_effect = raw.__getitem__
    factory = Mock(return_value=connection)
    result = collect_and_analyze_device(host="synthetic.example.invalid", port=22,
                                       username="<REDACTED>", password="<REDACTED>",
                                       connection_factory=factory)
    assert CANONICAL_EVIDENCE_COMMANDS == (
        "show running-config", "show version", "show ip interface brief", "show ip ssh",
        "show interfaces", "show access-lists", "show ntp associations", "show ip ospf neighbor")
    assert ALLOWED_COMMANDS == frozenset(CANONICAL_EVIDENCE_COMMANDS)
    assert tuple(call.args[0] for call in connection.send_command.call_args_list) == CANONICAL_EVIDENCE_COMMANDS
    factory.assert_called_once()
    connection.disconnect.assert_called_once_with()
    connection.enable.assert_not_called()
    connection.config_mode.assert_not_called()
    connection.send_config_set.assert_not_called()
    assert len(result.evidences) == 8 and len(result.operational_results) == 7
    assert len(result.configuration_evaluations) == 14
    assert tuple(item.rule_id for item in result.operational_evaluations) == ("IOS-IF-001",) + IDS
    assert len(result.evaluations) == len({item.rule_id for item in result.evaluations}) == 21
    assert len(result.findings) == findings
    assert [item.rule_id for item in result.findings] == [item.rule_id for item in result.evaluations if item.status == FAIL]
    assert {item.execution_id for item in result.evidences} == {result.execution_id}
    for item in result.evidences:
        assert item.sha256 == hashlib.sha256(item.raw_output.encode()).hexdigest()
        assert item.collected_at.utcoffset().total_seconds() == 0
    text = to_full_device_analysis_response(result).model_dump_json()
    for value in ("synthetic.example.invalid", "192.0.2.", "ACL-SINTETICA", "normalized_output", '"raw_output":'):
        assert value not in text


@pytest.mark.parametrize("forbidden", ["show interfaces detail", "show access-lists | include permit", "show ntp associations; reload", "show ip ospf neighbor\nconfigure terminal"])
def test_extended_allowlist_still_rejects_arbitrary_commands_before_connect(forbidden):
    factory = Mock()
    collector = NetmikoCollector("synthetic.example.invalid", 22, "<REDACTED>", "<REDACTED>", factory)
    with pytest.raises(CommandNotAllowedError):
        collector.collect(CANONICAL_EVIDENCE_COMMANDS + (forbidden,))
    factory.assert_not_called()


@pytest.mark.parametrize("rule_id,command", [
    ("IOS-INT-002", "show ip interface brief"),
    ("IOS-ACL-002", "show access-lists"),
    ("IOS-NTP-002", "show ntp associations"),
    ("IOS-AVL-001", "show interfaces"),
    ("IOS-OSPF-002", "show ip ospf neighbor"),
])
def test_wrong_structured_model_is_not_evaluated(rule_id, command):
    from ios_auditor.domain.models import ShowIpSshData
    ctx = context("hostname R1\n", {})
    wrong = OperationalContext(uuid4(), "synthetic.example.invalid", command,
                               datetime.now(timezone.utc), "a" * 64,
                               ShowIpSshData(True, "2.0", None, None))
    ctx = replace(ctx, operational=(wrong,))
    rule = next(item for item in get_expanded_operational_rules() if item.metadata.id == rule_id)
    result = rule.evaluate(ctx)
    assert result.status == NE and not findings_from_evaluations((result,))


@pytest.mark.parametrize("scenario", ["seguro", "inseguro", "no_evaluable"])
def test_campaign_summary_uses_full_observed_results(scenario):
    import importlib.util
    import sys
    path = ROOT / "scripts/evaluacion_2/run_validation_scenarios.py"
    spec = importlib.util.spec_from_file_location("full_campaign", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    selected = next(item for item in module.SCENARIOS if item.filename == f"escenario_{scenario}.cfg")
    result = module.run_integral_scenario(selected)
    assert result.success and len(result.comparisons) == 21
    assert "FUENTES SINTÉTICAS" in module.render_scenario(result)
    results = tuple(module.run_integral_scenario(item) for item in module.SCENARIOS)
    assert module.calculate_summary(results) == {
        "scenarios": 3, "rules_per_scenario": 21, "comparisons": 63,
        "matches": 63, "differences": 0, "pass": 32, "fail": 17,
        "not_evaluated": 14, "not_applicable": 0, "error": 0, "contract_errors": 0,
    }


@pytest.mark.parametrize("rule_id,severity,sources", [
    ("IOS-INT-002", "LOW", ("running-config", "show ip interface brief")),
    ("IOS-ACL-002", "MEDIUM", ("running-config", "show access-lists")),
    ("IOS-NTP-002", "MEDIUM", ("show ntp associations",)),
    ("IOS-AVL-001", "MEDIUM", ("show interfaces",)),
    ("IOS-OSPF-002", "HIGH", ("running-config", "show ip ospf neighbor")),
])
def test_metadata_and_rule_immutability(rule_id, severity, sources):
    rule = next(item for item in get_expanded_operational_rules() if item.metadata.id == rule_id)
    assert rule.expected_id == rule.metadata.id
    assert rule.metadata.default_severity.value == severity
    assert rule.metadata.required_sources == sources
    assert rule.metadata.false_positives and rule.metadata.recommendation
    with pytest.raises(FrozenInstanceError):
        rule.metadata = replace(rule.metadata, enabled=False)


def test_multisource_context_freezes_and_rejects_crossed_or_duplicate_sources():
    ctx = context("hostname R1\n", {"show interfaces": fixture_output("show interfaces")})
    with pytest.raises(FrozenInstanceError):
        ctx.configuration = ctx.configuration
    with pytest.raises(ValueError):
        replace(ctx, operational=ctx.operational * 2)
    crossed = replace(ctx.operational[0], command="show access-lists", execution_id=uuid4())
    with pytest.raises(ValueError):
        replace(ctx, operational=ctx.operational + (crossed,))


def test_operational_collections_copy_mutable_input():
    from ios_auditor.domain.operational_sources import ShowAccessListsData, AccessListEntry
    entries = [AccessListEntry("SYNTHETIC", "standard")]
    data = ShowAccessListsData(entries, True)
    entries.clear()
    assert isinstance(data.access_lists, tuple) and len(data.access_lists) == 1
    with pytest.raises(TypeError):
        ShowAccessListsData((object(),), True)


def test_multiple_interface_blocks_preserve_separate_counters():
    raw = "\n".join(fixture_output("show interfaces").splitlines()[:5]) + "\n"
    raw += "\n".join(fixture_output("show interfaces", "inseguro").splitlines()[:5]).replace("GigabitEthernet1", "GigabitEthernet2") + "\n"
    data = parse_show_command("show interfaces", raw)
    assert data.recognized
    assert [(item.name, item.input_errors) for item in data.interfaces] == [
        ("GigabitEthernet1", 0), ("GigabitEthernet2", 500)]
    check("IOS-AVL-001", "hostname R1\n", {"show interfaces": raw}, FAIL)


def test_numbered_standard_acl_and_hits_not_used_for_application():
    config = "access-list 10 permit 192.0.2.0 0.0.0.255\ninterface GigabitEthernet1\n ip access-group 10 in\n"
    show = "Standard IP access list 10\n    10 permit 192.0.2.0, wildcard bits 0.0.0.255 (0 matches)\n"
    check("IOS-ACL-002", config, {"show access-lists": show}, PASS)


@pytest.mark.parametrize("command", COMMANDS)
def test_partial_or_unknown_trailer_does_not_yield_safe_pass(command):
    raw = fixture_output(command) + "SECRET_MARKER unrecognized trailer\n"
    data = parse_show_command(command, raw)
    assert not data.recognized
    assert "SECRET_MARKER" not in repr(data)


def test_new_rule_count_is_dynamic_when_registry_changes(monkeypatch):
    import ios_auditor.services.full_device_analysis as module
    rules = get_expanded_operational_rules()
    selected = tuple(rule for rule in rules if rule.metadata.id != "IOS-OSPF-002")
    monkeypatch.setattr(module, "get_expanded_operational_rules", lambda: selected)
    connection = Mock()
    connection.send_command.side_effect = outputs().__getitem__
    result = collect_and_analyze_device(host="synthetic.example.invalid", port=22,
                                       username="<REDACTED>", password="<REDACTED>",
                                       connection_factory=Mock(return_value=connection))
    assert len(selected) == len(rules) - 1
    assert len(result.operational_evaluations) == 1 + len(selected)
    assert len(result.evaluations) == len(result.configuration_evaluations) + len(result.operational_evaluations)
    assert "IOS-OSPF-002" not in {item.rule_id for item in result.evaluations}


def test_rule_messages_do_not_leak_to_console_logs_or_findings(capsys, caplog):
    cfg = "ip access-list extended ACL-SINTETICA\n deny ip any any\n"
    check("IOS-ACL-002", cfg, {"show access-lists": fixture_output("show access-lists")}, FAIL)
    check("IOS-NTP-002", "hostname R1\n", {"show ntp associations": fixture_output("show ntp associations", "inseguro")}, FAIL)
    captured = capsys.readouterr()
    for value in ("192.0.2.", "ACL-SINTETICA", "SECRET_MARKER"):
        assert value not in caplog.text + captured.out + captured.err


def test_previous_four_command_batch_is_no_longer_integral():
    from ios_auditor.services import EvidenceBatchValidationError
    execution_id = uuid4()
    evidences = tuple(CommandEvidence(execution_id, "synthetic.example.invalid", command,
                                      datetime.now(timezone.utc), "", "",
                                      hashlib.sha256(b"").hexdigest())
                      for command in CANONICAL_EVIDENCE_COMMANDS[:4])
    with pytest.raises(EvidenceBatchValidationError) as captured:
        validate_evidence_batch(evidences)
    assert captured.value.code == "TOO_FEW_EVIDENCES"


def test_unknown_acl_consumer_reference_prevents_false_unapplied_finding():
    config = "interface GigabitEthernet1\n ip multicast boundary ACL-SINTETICA\n"
    config += "ip access-list extended ACL-SINTETICA\n deny ip any any\n"
    check("IOS-ACL-002", config, {"show access-lists": fixture_output("show access-lists")}, NE)
