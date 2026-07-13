from __future__ import annotations

from ios_auditor.domain import RuleStatus
from ios_auditor.rules.pilot import EnablePasswordRule, HttpServerRule, TelnetVtyRule
from ios_auditor.services.analyzer import load_context


def _context(tmp_path, content: str):
    path = tmp_path / "running.cfg"
    path.write_text(content, encoding="utf-8")
    return load_context(path)


def test_telnet_rule_pass(tmp_path):
    context = _context(tmp_path, "line vty 0 4\n transport input ssh\n")
    assert TelnetVtyRule().evaluate(context).status is RuleStatus.PASS


def test_telnet_rule_fail_for_any_protocol_order(tmp_path):
    context = _context(tmp_path, "line vty 0 4\n transport input ssh telnet\n")
    assert TelnetVtyRule().evaluate(context).status is RuleStatus.FAIL


def test_telnet_rule_not_evaluated_without_vty(tmp_path):
    context = _context(tmp_path, "hostname R1\n")
    assert TelnetVtyRule().evaluate(context).status is RuleStatus.NOT_EVALUATED


def test_http_rule_pass_for_secure_server(tmp_path):
    context = _context(tmp_path, "ip http secure-server\n")
    assert HttpServerRule().evaluate(context).status is RuleStatus.PASS


def test_http_rule_fail_for_exact_active_command(tmp_path):
    context = _context(tmp_path, "ip http server\n")
    assert HttpServerRule().evaluate(context).status is RuleStatus.FAIL


def test_enable_rule_pass_when_secret_exists(tmp_path):
    context = _context(
        tmp_path,
        "enable password <FAKE>\nenable secret <FAKE>\n",
    )
    assert EnablePasswordRule().evaluate(context).status is RuleStatus.PASS


def test_enable_rule_fail_and_redacts_password(tmp_path):
    context = _context(tmp_path, "enable password VALOR_FICTICIO\n")
    evaluation = EnablePasswordRule().evaluate(context)

    assert evaluation.status is RuleStatus.FAIL
    assert evaluation.evidence[0].content == "enable password <REDACTED>"
    assert "VALOR_FICTICIO" not in evaluation.evidence[0].content


def test_enable_rule_not_applicable_when_commands_are_absent(tmp_path):
    context = _context(tmp_path, "hostname R1\n")
    assert EnablePasswordRule().evaluate(context).status is RuleStatus.NOT_APPLICABLE
