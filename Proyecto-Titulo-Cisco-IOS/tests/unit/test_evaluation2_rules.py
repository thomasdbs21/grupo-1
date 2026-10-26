"""Contratos conservadores, evidencia sintética y aislamiento de los cinco controles."""

from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path
import socket
from unittest.mock import Mock

import paramiko
import pytest

from ios_auditor.domain import RuleStatus, Severity
from ios_auditor.rules import get_default_registry
from ios_auditor.rules.registry import RuleRegistry, RULE_TYPES, OFFICIAL_RULE_FILES
from ios_auditor.services.analyzer import analyze_bytes, analyze_context, load_context_from_bytes
from ios_auditor.services import CANONICAL_EVIDENCE_COMMANDS, collect_and_analyze_device
from ios_auditor.api.full_device_serialization import to_full_device_analysis_response
import ios_auditor.rules.evaluation2 as module

NEW_IDS = ("IOS-AUTH-002", "IOS-ACL-001", "IOS-OSPF-001", "IOS-SNMP-001", "IOS-DOC-001")
MARKER = "SYNTHETIC_SENSITIVE_MARKER_DO_NOT_DISCLOSE"
PASS, FAIL, NA, NE = (RuleStatus.PASS, RuleStatus.FAIL,
                      RuleStatus.NOT_APPLICABLE, RuleStatus.NOT_EVALUATED)


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Estas pruebas no deben abrir conexiones reales.")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(paramiko.SSHClient, "connect", forbidden)


def check(rule_id, content, expected):
    context = load_context_from_bytes(content.encode(), source_name="synthetic.cfg")
    before = asdict(context)
    registry = RuleRegistry()
    rule = get_default_registry().get(rule_id)
    registry.register(type(rule), rule.metadata)
    result = analyze_context(context, registry=registry)
    evaluation, = result.evaluations
    assert evaluation.status == expected
    assert asdict(context) == before
    assert bool(result.findings) == (expected == FAIL)
    assert [item.rule_id for item in result.findings] == ([rule_id] if expected == FAIL else [])
    assert evaluation.evidence
    for evidence in evaluation.evidence:
        assert evidence.source == "synthetic.cfg"
        assert evidence.sha256 == context.sha256
        if evidence.line_number is not None:
            assert 1 <= evidence.line_number <= len(content.splitlines())
        assert evidence.content == evaluation.message
    assert MARKER not in repr(result)
    return evaluation


@pytest.mark.parametrize("content,status", [
    (f"username ficticio secret {MARKER}\nline console 0\n login local\n", PASS),
    (f"username ficticio privilege 15 secret 9 {MARKER}\nline console 0\n login local\n", PASS),
    (f"line console 0\n password {MARKER}\n login\n", PASS),
    (f"line console 0\n\tpassword 7 {MARKER}\n\tlogin\n", PASS),
    (f"line console 0\n password 0 {MARKER}\n login\n", PASS),
    (f"aaa new-model\naaa authentication login CONS local\nusername ficticio secret {MARKER}\nline console 0\n login authentication CONS\n", PASS),
    (f"aaa new-model\naaa authentication login default local-case\nusername ficticio secret {MARKER}\nline console 0\n exec-timeout 5 0\n", PASS),
    ("line console 0\n no login\n", FAIL),
    (f"line console 0\n password {MARKER}\n", FAIL),
    ("line console 0\n login\n", FAIL),
    ("line console 0\n no password\n login\n", FAIL),
    ("aaa new-model\naaa authentication login CONS none\nline console 0\n login authentication CONS\n", FAIL),
    ("line console 0\n login local\n", NE),
    (f"username ficticio password {MARKER}\nline console 0\n login local\n", NE),
    ("hostname R1\n", NE),
    ("line console unknown\n login\n", NE),
    ("aaa new-model\nline console 0\n", NE),
    ("aaa new-model\naaa authentication login CONS group tacacs+ local\nline console 0\n login authentication CONS\n", NE),
    ("line console 0\n login authentication CONS\n", NE),
    (f"line console 0\n password 7\n login\n", NE),
    (f"line console 0\n password {MARKER}\n login\n login local\n", NE),
    (f"line console 0\n password {MARKER}\n login\n no login\n", NE),
    (f"line console 0\n password {MARKER}\n login\nline console 1\n no login\n", FAIL),
    ("aaa new-model\naaa authentication login default group radius\nline console 0\n no login\n", NE),
])
def test_console_contract(content, status):
    check("IOS-AUTH-002", content, status)


@pytest.mark.parametrize("content,status", [
    ("ip access-list extended SYNTHETIC\n permit ip any any\n", FAIL),
    ("ip access-list extended SYNTHETIC\n\t10 permit ip any any log\n", FAIL),
    ("access-list 100 permit ip any any log-input\n", FAIL),
    ("access-list 2699 permit ip 0.0.0.0 255.255.255.255 any\n", FAIL),
    ("access-list 2000 permit ip any 0.0.0.0 255.255.255.255\n", FAIL),
    ("access-list 199 permit ip any any\n", FAIL),
    ("ip access-list extended SYNTHETIC\n permit ip 192.0.2.7 255.255.255.255 any\n", FAIL),
    ("access-list 100 permit ip any 198.51.100.9 255.255.255.255\n", FAIL),
    ("ip access-list extended SYNTHETIC\n deny ip any any\n", PASS),
    ("ip access-list extended SYNTHETIC\n permit ip host 192.0.2.1 any\n", PASS),
    ("access-list 100 permit ip 192.0.2.0 0.0.0.255 any\n", PASS),
    ("access-list 100 permit tcp any any\n", PASS),
    ("access-list 100 deny icmp any any log\n", PASS),
    ("ip access-list extended SYNTHETIC\n remark permit ip any any\n deny ip any any\n", PASS),
    ("hostname R1\n", NA),
    ("access-list 99 permit any\n", NA),
    ("access-list 2700 permit ip any any\n", NA),
    ("ip access-list standard SYNTHETIC\n permit any\n", NA),
    ("ipv6 access-list SYNTHETIC\n permit ipv6 any any\n", NA),
    ("no access-list 100 permit ip any any\n", NA),
    ("no ip access-list extended SYNTHETIC\n", NA),
    ("ip access-list extended SYNTHETIC\n", NE),
    ("access-list 100 remark only-comment\n", NE),
    ("ip access-list extended SYNTHETIC\n permit ip any any time-range LIMITED\n", NE),
    ("access-list 100 permit tcp any any eq 22\n", NE),
    ("access-list 100 permit ip object-group SOURCE any\n", NE),
    ("access-list 100 permit ip host invalid any\n", NE),
    ("access-list malformed permit ip any any\n", NE),
    ("ip access-list extended\n permit ip any any\n", NE),
    ("ip access-list extended SYNTHETIC\n no permit ip any any\n deny ip any any\n", PASS),
    ("ip access-list extended SYNTHETIC\n permit ip any any\n unsupported syntax\n", FAIL),
])
def test_acl_contract(content, status):
    evaluation = check("IOS-ACL-001", content, status)
    assert "SYNTHETIC" not in repr(evaluation)
    assert "192.0.2." not in repr(evaluation)


def ospf(auth="", process="", extra="", address="ip address 192.0.2.1 255.255.255.0", binding="ip ospf 1 area 0"):
    children = "\n".join(" " + line for line in (address + "\n" + binding + "\n" + auth + "\n" + extra).splitlines() if line)
    return "router ospf 1\n" + process + "interface GigabitEthernet1\n" + children + "\n"


@pytest.mark.parametrize("content,status", [
    (ospf(f"ip ospf authentication message-digest\nip ospf message-digest-key 1 md5 {MARKER}"), PASS),
    (ospf(f"ip ospf message-digest-key 255 md5 7 {MARKER}", " area 0 authentication message-digest\n"), PASS),
    (ospf(f"ip ospf authentication\nip ospf authentication-key 0 {MARKER}"), PASS),
    (ospf(f"ip ospf authentication-key {MARKER}", " area 0.0.0.0 authentication\n"), PASS),
    (ospf(f"no ip ospf authentication\nip ospf message-digest-key 1 md5 {MARKER}", " area 0 authentication message-digest\n"), PASS),
    (ospf(), FAIL),
    (ospf("ip ospf authentication null", " area 0 authentication message-digest\n"), FAIL),
    (ospf(f"no ip ospf authentication-key {MARKER}"), FAIL),
    (ospf("", " no area 0 authentication message-digest\n"), FAIL),
    ("hostname R1\n", NA),
    ("no router ospf 1\n", NA),
    (ospf(extra="shutdown"), NA),
    (ospf(process=" passive-interface GigabitEthernet1\n"), NA),
    (ospf(process=" passive-interface default\n"), NA),
    (ospf(process=" passive-interface default\n no passive-interface GigabitEthernet1\n"), FAIL),
    ("router ospf 1\n", NE),
    ("router ospf 1\n network 192.0.2.0 0.0.0.255 area 0\n", NE),
    (ospf("ip ospf authentication message-digest"), NE),
    (ospf("ip ospf authentication message-digest\nip ospf message-digest-key 1 md5 7"), NE),
    (ospf(f"ip ospf authentication message-digest\nip ospf message-digest-key 0 md5 {MARKER}"), NE),
    (ospf("ip ospf authentication key-chain SYNTHETIC"), NE),
    (ospf("ip ospf authentication null\nip ospf authentication message-digest"), NE),
    (ospf("ip ospf authentication null\nno ip ospf authentication"), NE),
    (ospf(address="ip address dhcp"), NE),
    (ospf(address="ip address 999.0.0.1 255.255.255.0"), NE),
    (ospf(address="ip address 192.0.2.1 255.0.255.0"), NE),
    (ospf(address="ip address 192.0.2.1 0.0.0.255"), NE),
    (ospf(binding="ip ospf 1 area invalid"), NE),
    (ospf(binding="ip ospf 1 area 0\nip ospf 2 area 1"), NE),
    (ospf(extra="ip vrf forwarding SYNTHETIC"), NE),
    (ospf().replace("router ospf 1\n", ""), NE),
    (ospf().replace("router ospf 1", "router ospf 1 vrf SYNTHETIC"), NE),
    (ospf(process=" passive-interface GigabitEthernet1\n no passive-interface GigabitEthernet1\n"), NE),
])
def test_ospf_contract(content, status):
    evaluation = check("IOS-OSPF-001", content, status)
    assert "192.0.2." not in repr(evaluation)
    assert "GigabitEthernet1" not in repr(evaluation)


@pytest.mark.parametrize("content,status", [
    (f"snmp-server community {MARKER} RO\n", PASS),
    (f"snmp-server community {MARKER} view SYNTHETIC RO 99\n", PASS),
    (f"snmp-server community {MARKER} ro ACL-SYNTHETIC\n", PASS),
    ("snmp-server community public RO\n", FAIL),
    ("snmp-server community PRIVATE RO\n", FAIL),
    (f"snmp-server community {MARKER} RW\n", FAIL),
    (f"snmp-server community {MARKER} view SYNTHETIC rw ACL-SYNTHETIC\n", FAIL),
    ("hostname R1\n", NA),
    ("no snmp-server community public RO\n", NA),
    ("snmp-server group SYNTHETIC v3 priv\n", NE),
    ("snmp-server community\n", NE),
    (f"snmp-server community {MARKER}\n", PASS),
    ("snmp-server community public\n", FAIL),
    ("snmp-server community private\n", FAIL),
    (f"snmp-server community {MARKER} view SYNTHETIC\n", PASS),
    (f"snmp-server community 7 {MARKER} RO\n", NE),
    (f"snmp-server community \"{MARKER}\" RO\n", NE),
    (f"snmp-server community {MARKER} view\n", NE),
    (f"snmp-server community {MARKER} RO ipv6 ACL-SYNTHETIC\n", NE),
    (f"snmp-server community {MARKER} RO ipv6\n", NE),
    (f"snmp-server community {MARKER} RO\nsnmp-server community incomplete view\n", NE),
    ("snmp-server community public RO\nsnmp-server community incomplete view\n", FAIL),
])
def test_snmp_contract(content, status):
    evaluation = check("IOS-SNMP-001", content, status)
    for value in ("public", "PRIVATE", "SYNTHETIC", "ACL-SYNTHETIC"):
        assert value not in repr(evaluation)


@pytest.mark.parametrize("content,status", [
    ("hostname R1\n", PASS),
    ("hostname X\n", PASS),
    ("hostname 1\n", PASS),
    ("hostname ROUTER-SEGURO\n", PASS),
    ("hostname site.example.invalid\n", PASS),
    ("hostname Router\n", FAIL),
    ("hostname SWITCH\n", FAIL),
    ("version 16.9\n", FAIL),
    ("no hostname\n", FAIL),
    ("hostname\n", NE),
    ("hostname invalid extra\n", NE),
    ("hostname -invalid\n", NE),
    ("hostname R1\nhostname R2\n", NE),
])
def test_hostname_contract(content, status):
    check("IOS-DOC-001", content, status)


@pytest.mark.parametrize("rule_id,severity", list(zip(NEW_IDS, (Severity.MEDIUM, Severity.HIGH, Severity.HIGH, Severity.HIGH, Severity.LOW))))
def test_metadata_registry_and_immutability(rule_id, severity):
    rule = get_default_registry().get(rule_id)
    metadata = rule.metadata
    assert metadata.default_severity == severity
    assert metadata.required_sources == ("running-config",)
    assert metadata.version == "1.0.0" and metadata.enabled
    assert metadata.references and all("https://www.cisco.com/" in item for item in metadata.references)
    assert metadata.risk and metadata.recommendation and metadata.false_positives
    assert rule_id + ".yaml" in OFFICIAL_RULE_FILES
    with pytest.raises(FrozenInstanceError):
        rule.metadata = replace(metadata, enabled=False)


@pytest.mark.parametrize("rule_id", NEW_IDS)
def test_internal_errors_are_error_and_never_leak_secret(rule_id, monkeypatch):
    def broken(_):
        raise RuntimeError(MARKER)
    monkeypatch.setattr(module, "_blocks", broken)
    registry = RuleRegistry()
    rule = get_default_registry().get(rule_id)
    registry.register(type(rule), rule.metadata)
    result = analyze_bytes(b"hostname R1\n", source_name="synthetic.cfg", registry=registry)
    assert result.evaluations[0].status == RuleStatus.ERROR
    assert not result.findings and MARKER not in repr(result)


@pytest.mark.parametrize("rule_id,content,status", [
    ("IOS-DOC-001", "! hostname Router\nhostname R1\n", PASS),
    ("IOS-SNMP-001", "interface GigabitEthernet1\n description snmp-server community public RW\n", NA),
    ("IOS-ACL-001", "banner motd ^C\nip access-list extended FAKE\n permit ip any any\n^C\nhostname R1\n", NA),
    ("IOS-AUTH-002", f"banner motd #\nline console 0\n password {MARKER}\n login\n#\nhostname R1\n", NE),
    ("IOS-DOC-001", "banner motd #inline#\nhostname R1\n", PASS),
])
def test_comments_banners_and_unrelated_sections_are_excluded(rule_id, content, status):
    check(rule_id, content, status)


@pytest.mark.parametrize("scenario,findings", [("seguro", 0), ("inseguro", 13), ("no_evaluable", 0)])
def test_full_public_flow_expands_dynamically_without_network(scenario, findings):
    project = Path(__file__).resolve().parents[2]
    config = (project / f"samples/evaluacion_2/escenario_{scenario}.cfg").read_text(encoding="utf-8")
    config = config.replace("<REDACTED>", MARKER).replace("<REDACTED-COMMUNITY>", MARKER).replace("<REDACTED-OSPF>", MARKER)
    outputs = {
        "show running-config": config,
        "show version": "Cisco IOS XE Software, Version 16.09.05\n",
        "show ip interface brief": "Interface IP-Address OK? Method Status Protocol\nGigabitEthernet1 192.0.2.1 YES manual up up\n",
        "show ip ssh": "SSH Enabled - version 2.0\nAuthentication timeout: 120 secs; Authentication retries: 3\n",
    }
    connection = Mock()
    outputs.update({
        "show interfaces": "GigabitEthernet1 is down, line protocol is down\n",
        "show access-lists": "",
        "show ntp associations": "address ref clock st when poll reach delay offset disp\n",
        "show ip ospf neighbor": "Neighbor ID Pri State Dead Time Address Interface\n",
    })
    connection.send_command.side_effect = outputs.__getitem__
    factory = Mock(return_value=connection)
    result = collect_and_analyze_device(host="device.example.invalid", port=22,
                                       username="<REDACTED>", password="<REDACTED>",
                                       connection_factory=factory)
    ids = tuple(rule.expected_id for rule in get_default_registry().list_rules(enabled_only=True))
    assert tuple(item.rule_id for item in result.configuration_evaluations) == ids
    assert len(ids) == len(RULE_TYPES) == 14
    assert tuple(item.rule_id for item in result.evaluations) == ids + (
        "IOS-IF-001", "IOS-INT-002", "IOS-ACL-002", "IOS-NTP-002", "IOS-AVL-001", "IOS-OSPF-002", "IOS-INT-001")
    assert len(result.evaluations) == 21 and len({item.rule_id for item in result.evaluations}) == 21
    assert len(result.evidences) == 8 and len(result.operational_results) == 7
    assert {item.execution_id for item in result.evidences} == {result.execution_id}
    assert tuple(call.args[0] for call in connection.send_command.call_args_list) == CANONICAL_EVIDENCE_COMMANDS
    factory.assert_called_once()
    connection.disconnect.assert_called_once_with()
    connection.enable.assert_not_called()
    connection.config_mode.assert_not_called()
    connection.send_config_set.assert_not_called()
    assert len(result.findings) == findings
    assert [item.rule_id for item in result.findings] == [item.rule_id for item in result.evaluations if item.status == FAIL]
    dto = to_full_device_analysis_response(result).model_dump_json()
    for forbidden in (MARKER, "192.0.2.", "device.example.invalid", "ACL-SINTETICA", '"raw_output":', "normalized_output"):
        assert forbidden not in dto


@pytest.mark.parametrize("rule_id", NEW_IDS)
def test_each_new_rule_can_be_disabled_without_evaluation_or_finding(rule_id):
    registry = RuleRegistry()
    for rule in get_default_registry().list_rules():
        metadata = replace(rule.metadata, enabled=False) if rule.metadata.id == rule_id else rule.metadata
        registry.register(type(rule), metadata)
    project = Path(__file__).resolve().parents[2]
    raw = (project / "samples/evaluacion_2/escenario_inseguro.cfg").read_bytes()
    result = analyze_bytes(raw, source_name="synthetic.cfg", registry=registry)
    assert len(result.evaluations) == len(RULE_TYPES) - 1
    assert rule_id not in [item.rule_id for item in result.evaluations]
    assert rule_id not in [item.rule_id for item in result.findings]


@pytest.mark.parametrize("rule_id,content,status", [
    ("IOS-AUTH-002", f"line console 0\n password {MARKER}\n", FAIL),
    ("IOS-OSPF-001", ospf(f"ip ospf authentication message-digest\nip ospf message-digest-key 1 md5 {MARKER}"), PASS),
    ("IOS-SNMP-001", f"snmp-server community {MARKER} RW\n", FAIL),
])
def test_secrets_do_not_reach_logs_console_or_finding(rule_id, content, status, capsys, caplog):
    evaluation = check(rule_id, content, status)
    assert MARKER not in repr(evaluation)
    assert MARKER not in caplog.text
    captured = capsys.readouterr()
    assert MARKER not in captured.out + captured.err


@pytest.mark.parametrize("rule_id,content,line", [
    ("IOS-AUTH-002", "hostname R1\nline console 0\n no login\n", 2),
    ("IOS-ACL-001", "ip access-list extended SYNTHETIC\n permit ip any any\n", 2),
    ("IOS-OSPF-001", ospf(), 2),
    ("IOS-SNMP-001", "hostname R1\nsnmp-server community public RO\n", 2),
    ("IOS-DOC-001", "version 16.9\nhostname Router\n", 2),
])
def test_fail_evidence_points_to_relevant_section_or_directive(rule_id, content, line):
    evaluation = check(rule_id, content, FAIL)
    assert evaluation.evidence[0].line_number == line


def test_ospf_all_applicable_interfaces_must_be_authenticated():
    content = ospf(f"ip ospf authentication message-digest\nip ospf message-digest-key 1 md5 {MARKER}")
    content += "interface GigabitEthernet2\n ip address 198.51.100.1 255.255.255.0\n ip ospf 1 area 0\n"
    check("IOS-OSPF-001", content, FAIL)


def test_ospf_proven_failure_precedes_another_ambiguous_process():
    check("IOS-OSPF-001", ospf() + "router ospf 2\n", FAIL)


def test_ospf_pass_never_hides_another_ambiguous_process():
    content = ospf(f"ip ospf authentication message-digest\nip ospf message-digest-key 1 md5 {MARKER}")
    check("IOS-OSPF-001", content + "router ospf 2\n", NE)
