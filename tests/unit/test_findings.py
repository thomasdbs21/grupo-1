from __future__ import annotations

from ios_auditor.domain import RuleStatus
from ios_auditor.services.analyzer import analyze_file


def test_findings_are_created_only_from_fail(tmp_path):
    path = tmp_path / "running.cfg"
    path.write_text(
        "enable secret <FAKE>\nip http server\nip ssh version 2\n"
        "ntp server 192.0.2.10\nlogging host 192.0.2.20\n"
        "line vty 0 4\n transport input ssh\n",
        encoding="utf-8",
    )

    result = analyze_file(path)

    assert len(result.findings) == 1
    assert result.findings[0].rule_id == "IOS-SRV-001"
    assert all(
        evaluation.status is RuleStatus.FAIL
        for evaluation in result.evaluations
        if evaluation.rule_id in {finding.rule_id for finding in result.findings}
    )
