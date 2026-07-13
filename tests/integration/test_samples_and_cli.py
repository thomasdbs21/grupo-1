from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ios_auditor.domain import RuleStatus
from ios_auditor.services.analyzer import analyze_file


ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "samples"


def test_incorrect_sample_has_exactly_three_findings():
    result = analyze_file(SAMPLES / "running_config_incorrecta.cfg")
    assert len(result.evaluations) == 3
    assert len(result.findings) == 3
    assert all(item.status is RuleStatus.FAIL for item in result.evaluations)


def test_correct_sample_has_no_findings_and_all_pass():
    result = analyze_file(SAMPLES / "running_config_correcta.cfg")
    assert len(result.findings) == 0
    assert all(item.status is RuleStatus.PASS for item in result.evaluations)


def test_incomplete_sample_has_no_false_findings():
    result = analyze_file(SAMPLES / "running_config_incompleta.cfg")
    statuses = {item.rule_id: item.status for item in result.evaluations}
    assert len(result.findings) == 0
    assert statuses["IOS-ADM-001"] is RuleStatus.NOT_EVALUATED
    assert statuses["IOS-AUTH-001"] is RuleStatus.NOT_APPLICABLE


def test_cli_outputs_valid_json():
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "ios_auditor",
            "analyze",
            str(SAMPLES / "running_config_incorrecta.cfg"),
            "--pretty",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    output = json.loads(completed.stdout)
    assert len(output["findings"]) == 3


def test_cli_returns_nonzero_for_invalid_input():
    completed = subprocess.run(
        [sys.executable, "-m", "ios_auditor", "analyze", "missing.cfg"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "error" in json.loads(completed.stderr)
