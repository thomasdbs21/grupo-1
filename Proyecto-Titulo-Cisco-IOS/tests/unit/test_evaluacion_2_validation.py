"""Campaña local y wrapper manual comprobados sin acceso a la red."""

from __future__ import annotations

from dataclasses import replace
import getpass
import importlib.util
from pathlib import Path
import socket
import sys
from unittest.mock import Mock

import paramiko
import pytest

from ios_auditor.domain import RuleStatus
from ios_auditor.rules import get_default_registry

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str):
    path = PROJECT_ROOT / "scripts" / "evaluacion_2" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"eval2_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def forbid_real_ssh(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Las pruebas de Evaluación 2 no deben abrir conexiones de red.")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(paramiko.SSHClient, "connect", forbidden)


@pytest.fixture
def offline():
    return load_script("run_validation_scenarios")


@pytest.fixture
def manual():
    return load_script("run_csr1000v_validation")


@pytest.mark.parametrize("key,statuses,finding_count", [
    ("seguro", ["PASS"] * 14, 0),
    ("inseguro", ["FAIL"] * 5 + ["PASS"] * 2 + ["FAIL"] * 7, 12),
    ("no-evaluable", ["PASS", "PASS", "PASS", "NOT_EVALUATED", "PASS", "PASS", "PASS"] + ["NOT_EVALUATED"] * 4 + ["PASS"] + ["NOT_EVALUATED"] * 2, 0),
])
def test_scenarios_reuse_real_rules_and_match_declared_expectations(
    offline, key, statuses, finding_count,
):
    scenario = next(item for item in offline.SCENARIOS if item.key == key)
    registry_ids = tuple(rule.metadata.id for rule in get_default_registry().list_rules())
    assert tuple(rule_id for rule_id, _ in scenario.expected) == registry_ids
    assert [status.value for _, status in scenario.expected] == statuses
    result = offline.run_scenario(scenario)
    assert [row.obtained.value for row in result.comparisons] == statuses
    assert result.success
    analysis = offline.analyze_file(
        PROJECT_ROOT / "samples" / "evaluacion_2" / scenario.filename
    )
    assert len(analysis.findings) == finding_count
    assert [finding.rule_id for finding in analysis.findings] == [
        item.rule_id for item in analysis.evaluations if item.status == RuleStatus.FAIL
    ]


def test_summary_is_computed_from_observed_comparisons(offline):
    results = tuple(offline.run_scenario(item) for item in offline.SCENARIOS)
    assert offline.calculate_summary(results) == {
        "scenarios": 3, "rules_per_scenario": 14, "comparisons": 42,
        "matches": 42, "differences": 0, "pass": 23, "fail": 12,
        "not_evaluated": 7, "not_applicable": 0, "error": 0, "contract_errors": 0,
    }
    changed_row = replace(results[0].comparisons[0], obtained=RuleStatus.FAIL)
    changed_result = replace(
        results[0], comparisons=(changed_row,) + results[0].comparisons[1:]
    )
    changed = offline.calculate_summary((changed_result,) + results[1:])
    assert changed["matches"] == 41
    assert changed["differences"] == 1
    assert changed["pass"] == 22
    assert not changed_result.success
    assert "RESULTADO: DIFERENCIA" in offline.render_summary((changed_result,))


def test_clean_capture_format_contains_no_configuration(offline):
    result = offline.run_scenario(offline.SCENARIOS[1])
    text = offline.render_scenario(result)
    assert "Esperado" in text and "Obtenido" in text and "Verificación" in text
    assert "IOS-ADM-001" in text and "FAIL" in text and "14/14" in text
    for forbidden in ("192.0.2.", "<REDACTED>", "enable password", "hostname", "ntp server"):
        assert forbidden not in text
    summary = offline.render_summary((result,))
    assert "Comparaciones totales: 14" in summary
    assert "FAIL verificados: 12" in summary


@pytest.mark.parametrize("change", ["missing", "unexpected", "order", "findings"])
def test_contract_differences_are_visible_and_never_pass(offline, monkeypatch, change):
    scenario = offline.SCENARIOS[1]
    original = offline.analyze_file(
        PROJECT_ROOT / "samples" / "evaluacion_2" / scenario.filename
    )
    evaluations = original.evaluations
    findings = original.findings
    if change == "missing":
        evaluations = evaluations[1:]
    elif change == "unexpected":
        evaluations += (replace(evaluations[0], rule_id="SYNTHETIC-EXTRA"),)
    elif change == "order":
        evaluations = tuple(reversed(evaluations))
    else:
        findings = ()
    monkeypatch.setattr(
        offline, "analyze_file",
        lambda _: replace(original, evaluations=evaluations, findings=findings),
    )
    result = offline.run_scenario(scenario)
    assert not result.success
    assert "DIFERENCIA" in offline.render_scenario(result)


@pytest.mark.parametrize("argv", [[], ["--summary-only"], ["--scenario", "inseguro"]])
def test_offline_entrypoints_never_open_ssh(offline, argv, capsys):
    assert offline.main(argv) == 0
    assert "RESULTADO: OK" in capsys.readouterr().out


def test_cli_returns_failure_when_expectation_does_not_match(offline, monkeypatch, capsys):
    scenario = offline.SCENARIOS[0]
    wrong = replace(
        scenario, expected=(("IOS-ADM-001", RuleStatus.FAIL),) + scenario.expected[1:]
    )
    monkeypatch.setattr(offline, "SCENARIOS", (wrong,))
    assert offline.main(["--summary-only"]) == 1
    assert "Diferencias: 1" in capsys.readouterr().out


def test_importing_scripts_does_not_prompt_or_connect(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Importar un script no debe solicitar credenciales ni conectar.")
    monkeypatch.setattr("builtins.input", forbidden)
    monkeypatch.setattr(getpass, "getpass", forbidden)
    load_script("run_validation_scenarios")
    load_script("run_csr1000v_validation")


class FakeReadOnlyConnection:
    def __init__(self, running_config: str):
        self.commands = []
        self.disconnected = False
        self.outputs = {
            "show running-config": running_config,
            "show version": "Cisco IOS XE Software, Version 16.09.05\n",
            "show ip interface brief": (
                "Interface IP-Address OK? Method Status Protocol\n"
                "GigabitEthernet1 192.0.2.30 YES manual up up\n"
            ),
            "show ip ssh": (
                "SSH Enabled - version 2.0\n"
                "Authentication timeout: 120 secs; Authentication retries: 3\n"
            ),
        }

        self.outputs.update({
            "show interfaces": "GigabitEthernet1 is down, line protocol is down\n",
            "show access-lists": "",
            "show ntp associations": "address ref clock st when poll reach delay offset disp\n",
            "show ip ospf neighbor": "Neighbor ID Pri State Dead Time Address Interface\n",
        })

    def send_command(self, command_string: str) -> str:
        self.commands.append(command_string)
        return self.outputs[command_string]

    def disconnect(self) -> None:
        self.disconnected = True


def test_manual_wrapper_uses_full_real_service_with_fake_transport_only(
    manual, monkeypatch, capsys,
):
    config = (PROJECT_ROOT / "samples/evaluacion_2/escenario_inseguro.cfg").read_text()
    connection = FakeReadOnlyConnection(config)
    factory = Mock(return_value=connection)
    monkeypatch.setattr(manual.netmiko_collector, "ConnectHandler", factory)
    inputs = iter(("device.example.invalid", "22", "<REDACTED_USER>", "<REDACTED_PASSWORD>"))
    monkeypatch.setattr(manual, "hidden_input", lambda _: next(inputs))
    assert manual.main() == 0
    factory.assert_called_once_with(
        device_type="cisco_ios", host="device.example.invalid", port=22,
        username="<REDACTED_USER>", password="<REDACTED_PASSWORD>",
    )
    assert tuple(connection.commands) == manual.CANONICAL_EVIDENCE_COMMANDS
    assert connection.disconnected
    text = capsys.readouterr().out
    for expected in ("Evidencias recopiladas: 8", "Evaluaciones ejecutadas: 21",
                     "Findings: 13", "Sesiones SSH: 1", "IOS-IF-001",
                     "Plataforma: Cisco IOS XE"):
        assert expected in text
    for forbidden in ("device.example.invalid", "REDACTED", "192.0.2.",
                      "enable password", "raw_output", "normalized_output"):
        assert forbidden not in text


def test_manual_errors_are_sanitized_and_not_retried(manual, monkeypatch, capsys):
    inputs = iter(("device.example.invalid", "22", "<REDACTED_USER>", "<REDACTED_PASSWORD>"))
    monkeypatch.setattr(manual, "hidden_input", lambda _: next(inputs))
    factory = Mock(side_effect=RuntimeError("PRIVATE_SECRET 192.0.2.99"))
    monkeypatch.setattr(manual.netmiko_collector, "ConnectHandler", factory)
    assert manual.main() == 1
    factory.assert_called_once()
    text = capsys.readouterr().out
    assert "ERROR:" in text and "No se reintentará SSH" in text
    assert "PRIVATE_SECRET" not in text and "192.0.2." not in text
    assert "Traceback" not in text


@pytest.mark.parametrize("port", ["0", "65536", "no-numero"])
def test_invalid_input_does_not_connect(manual, monkeypatch, port):
    inputs = iter(("device.example.invalid", port, "<REDACTED_USER>", "<REDACTED_PASSWORD>"))
    monkeypatch.setattr(manual, "hidden_input", lambda _: next(inputs))
    factory = Mock()
    monkeypatch.setattr(manual.netmiko_collector, "ConnectHandler", factory)
    assert manual.main() == 1
    factory.assert_not_called()


def test_hidden_input_refuses_visible_fallback(manual, monkeypatch):
    def fallback(_):
        import warnings
        warnings.warn("Echo unavailable", getpass.GetPassWarning)
        pytest.fail("No debe llegar a leer credenciales en modo visible.")
    monkeypatch.setattr(getpass, "getpass", fallback)
    with pytest.raises(getpass.GetPassWarning):
        manual.hidden_input("Contraseña: ")


def test_audited_factory_refuses_second_session_and_extra_commands(manual, monkeypatch):
    connection = FakeReadOnlyConnection("synthetic")
    factory = Mock(return_value=connection)
    monkeypatch.setattr(manual.netmiko_collector, "ConnectHandler", factory)
    audit = manual.SessionAudit()
    audited = manual.audited_factory(audit)
    restricted = audited()
    with pytest.raises(ValueError):
        audited()
    with pytest.raises(ValueError):
        restricted.send_command("configure terminal")
    assert connection.commands == []
    factory.assert_called_once()
