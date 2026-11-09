# Contrasta habilitación, negación y ambigüedad de Finger, PAD y source routing.
"""Casos de política global explícita. Los datos son sintéticos."""

import pytest

from ios_auditor.domain import RuleStatus
from ios_auditor.services.analyzer import analyze_bytes


@pytest.mark.parametrize("identifier,command,severity", [
    ("IOS-SRV-003", "ip finger", "LOW"),
    ("IOS-SRV-003", "service finger", "LOW"),
    ("IOS-SRV-004", "service pad", "LOW"),
    ("IOS-IP-002", "ip source-route", "MEDIUM"),
])
@pytest.mark.parametrize("template,status", [
    ("{cmd}", "FAIL"), ("no {cmd}", "PASS"),
    ("hostname demo", "NOT_EVALUATED"),
    ("default {cmd}", "NOT_EVALUATED"), ("{cmd} inesperado", "NOT_EVALUATED"),
    ("{cmd}\nno {cmd}", "NOT_EVALUATED"),
    ("interface Loopback0\n {cmd}", "NOT_EVALUATED"),
    ("macro name demo\n{cmd}\n@", "NOT_EVALUATED"),
    ("banner motd ^\n{cmd}\n^", "NOT_EVALUATED"),
])
def test_explicit_policy(identifier, command, severity, template, status):
    config = "hostname demo\n" + template.format(cmd=command) + "\nend\n"
    result = analyze_bytes(config.encode(), source_name="demo.cfg")
    evaluation = next(row for row in result.evaluations if row.rule_id == identifier)
    assert evaluation.status is RuleStatus(status)
    assert evaluation.severity.value == severity
    assert evaluation.recommendation
    assert bool([f for f in result.findings if f.rule_id == identifier]) == (status == "FAIL")
    if status in {"PASS", "FAIL"}:
        assert evaluation.evidence[0].line_number == 2
        assert evaluation.evidence[0].sha256


def test_finger_aliases_cannot_hide_conflicting_directives():
    result = analyze_bytes(b"ip finger\nno service finger\n", source_name="demo.cfg")
    row = next(r for r in result.evaluations if r.rule_id == "IOS-SRV-003")
    assert row.status is RuleStatus.NOT_EVALUATED
