from __future__ import annotations

import hashlib
from dataclasses import fields
from datetime import datetime, timezone
from unittest.mock import MagicMock, call
from uuid import UUID, uuid4

import pytest

from ios_auditor.collectors import CommandEvidence
from ios_auditor.domain import (
    AnalysisResult,
    Evidence,
    Finding,
    FullDeviceAnalysisResult,
    RuleEvaluation,
    RuleStatus,
    Severity,
)
from ios_auditor.domain.models import (
    OperationalContext,
    ShowIpInterfaceBriefData,
    ShowIpSshData,
    ShowVersionData,
)
from ios_auditor.services import (
    AnalysisError,
    CANONICAL_EVIDENCE_COMMANDS,
    FullDeviceAnalysisContractError,
    OperationalAnalysisError,
    ValidatedEvidenceBatch,
    analyze_validated_evidence_batch,
    validate_evidence_batch,
)
import ios_auditor.services.full_device_analysis as service_module
import ios_auditor.services.rule_results as rule_results_module
from ios_auditor.services.rule_results import findings_from_evaluations


DEVICE = "device.example.invalid"
RUNNING_CONFIG = (
    "line vty 0 4\n"
    " transport input ssh\n"
    "ip http secure-server\n"
)
SHOW_VERSION = "Cisco IOS XE Software, Version 16.09.05\n"
SHOW_INTERFACES = (
    "Interface IP-Address OK? Method Status Protocol\n"
    "GigabitEthernet1 unassigned YES unset up down\n"
)
SHOW_SSH = (
    "SSH Enabled - version 2.0\n"
    "Authentication timeout: 120 secs; Authentication retries: 3\n"
)
RAW_OUTPUTS = {
    "show running-config": RUNNING_CONFIG,
    "show version": SHOW_VERSION,
    "show ip interface brief": SHOW_INTERFACES,
    "show ip ssh": SHOW_SSH,
}


def _evidence(command: str, execution_id: UUID) -> CommandEvidence:
    raw_output = RAW_OUTPUTS[command]
    return CommandEvidence(
        execution_id=execution_id,
        device_host=DEVICE,
        command=command,
        collected_at=datetime.now(timezone.utc),
        raw_output=raw_output,
        normalized_output=raw_output.replace("\r\n", "\n").replace("\r", "\n"),
        sha256=hashlib.sha256(raw_output.encode("utf-8")).hexdigest(),
    )


def _batch() -> ValidatedEvidenceBatch:
    execution_id = uuid4()
    return validate_evidence_batch(
        _evidence(command, execution_id)
        for command in reversed(CANONICAL_EVIDENCE_COMMANDS)
    )


def _evaluation(
    rule_id: str,
    status: RuleStatus,
) -> RuleEvaluation:
    return RuleEvaluation(
        rule_id=rule_id,
        rule_name=f"Rule {rule_id}",
        status=status,
        severity=Severity.MEDIUM,
        message="Resultado técnico sintético.",
        recommendation="Recomendación técnica sintética.",
    )


def _finding(evaluation: RuleEvaluation) -> Finding:
    return Finding(
        rule_id=evaluation.rule_id,
        rule_name=evaluation.rule_name,
        severity=evaluation.severity,
        message=evaluation.message,
        recommendation=evaluation.recommendation,
        evidence=evaluation.evidence,
    )


def _configuration_result(batch: ValidatedEvidenceBatch) -> AnalysisResult:
    evaluation = _evaluation("IOS-ADM-001", RuleStatus.PASS)
    return AnalysisResult(
        source_path="full-device-running-config",
        sha256=batch.evidence_for("show running-config").sha256,
        evaluations=(evaluation,),
        findings=(),
    )


def _operational_context(evidence: CommandEvidence) -> OperationalContext:
    if evidence.command == "show version":
        data = ShowVersionData("test-version", None, None, None)
    elif evidence.command == "show ip interface brief":
        data = ShowIpInterfaceBriefData(interfaces=())
    else:
        data = ShowIpSshData(True, "2.0", 120, 3)
    return OperationalContext(
        execution_id=evidence.execution_id,
        device_host=evidence.device_host,
        command=evidence.command,
        collected_at=evidence.collected_at,
        sha256=evidence.sha256,
        data=data,
    )


@pytest.fixture
def wired_flow(monkeypatch):
    batch = _batch()
    configuration_result = _configuration_result(batch)
    operational_contexts = {
        command: _operational_context(batch.evidence_for(command))
        for command in CANONICAL_EVIDENCE_COMMANDS[1:]
    }
    operational_evaluation = _evaluation("IOS-IF-001", RuleStatus.FAIL)
    operational_finding = _finding(operational_evaluation)

    analyzer = MagicMock(return_value=configuration_result)
    parser = MagicMock(
        side_effect=lambda evidence: operational_contexts[evidence.command]
    )
    rule = MagicMock()
    rule.evaluate.return_value = operational_evaluation
    rule_loader = MagicMock(return_value=rule)
    finding_builder = MagicMock(return_value=(operational_finding,))

    monkeypatch.setattr(service_module, "analyze_bytes", analyzer)
    monkeypatch.setattr(service_module, "parse_collected_show_evidence", parser)
    monkeypatch.setattr(service_module, "get_interface_operational_rule", rule_loader)
    monkeypatch.setattr(
        service_module,
        "findings_from_evaluations",
        finding_builder,
    )
    return {
        "batch": batch,
        "configuration_result": configuration_result,
        "operational_contexts": operational_contexts,
        "operational_evaluation": operational_evaluation,
        "operational_finding": operational_finding,
        "analyzer": analyzer,
        "parser": parser,
        "rule": rule,
        "rule_loader": rule_loader,
        "finding_builder": finding_builder,
    }


def test_builds_full_result_and_preserves_execution_and_evidences(wired_flow):
    batch = wired_flow["batch"]

    result = analyze_validated_evidence_batch(batch)

    assert isinstance(result, FullDeviceAnalysisResult)
    assert result.execution_id is batch.execution_id
    assert all(
        actual is original
        for actual, original in zip(result.evidences, batch.evidences, strict=True)
    )


def test_configuration_analysis_receives_only_running_config_once(wired_flow):
    batch = wired_flow["batch"]
    running_config = batch.evidence_for("show running-config")

    analyze_validated_evidence_batch(batch)

    wired_flow["analyzer"].assert_called_once_with(
        running_config.raw_output.encode("utf-8"),
        source_name="full-device-running-config",
    )
    assert running_config.device_host not in wired_flow["analyzer"].call_args.kwargs[
        "source_name"
    ]


def test_each_operational_evidence_is_parsed_once_without_crossing(wired_flow):
    batch = wired_flow["batch"]

    analyze_validated_evidence_batch(batch)

    wired_flow["parser"].assert_has_calls(
        [
            call(batch.evidence_for("show version")),
            call(batch.evidence_for("show ip interface brief")),
            call(batch.evidence_for("show ip ssh")),
        ]
    )
    assert wired_flow["parser"].call_count == 3
    assert all(
        parsed_evidence.command != "show running-config"
        for parsed_evidence, in (
            recorded_call.args for recorded_call in wired_flow["parser"].call_args_list
        )
    )


def test_operational_rule_runs_once_only_on_interface_context(wired_flow):
    analyze_validated_evidence_batch(wired_flow["batch"])

    wired_flow["rule_loader"].assert_called_once_with()
    wired_flow["rule"].evaluate.assert_called_once_with(
        wired_flow["operational_contexts"]["show ip interface brief"]
    )


def test_preserves_results_evaluations_findings_and_official_order(wired_flow):
    result = analyze_validated_evidence_batch(wired_flow["batch"])

    assert result.configuration_result is wired_flow["configuration_result"]
    expected_contexts = tuple(
        wired_flow["operational_contexts"][command]
        for command in CANONICAL_EVIDENCE_COMMANDS[1:]
    )
    assert all(
        actual is expected
        for actual, expected in zip(
            result.operational_results,
            expected_contexts,
            strict=True,
        )
    )
    assert result.operational_evaluations[0] is wired_flow[
        "operational_evaluation"
    ]
    assert result.operational_findings[0] is wired_flow["operational_finding"]
    assert result.evaluations == (
        result.configuration_evaluations + result.operational_evaluations
    )
    assert result.findings == (
        result.configuration_findings + result.operational_findings
    )


def test_findings_are_derived_once_from_operational_evaluations(wired_flow):
    result = analyze_validated_evidence_batch(wired_flow["batch"])

    wired_flow["finding_builder"].assert_called_once_with(
        result.operational_evaluations
    )


@pytest.mark.parametrize(
    "status",
    (
        RuleStatus.PASS,
        RuleStatus.NOT_APPLICABLE,
        RuleStatus.NOT_EVALUATED,
        RuleStatus.ERROR,
    ),
)
def test_shared_finding_utility_ignores_every_non_fail_status(status):
    evaluation = _evaluation("IOS-TEST-001", status)

    findings = findings_from_evaluations((evaluation,))

    assert findings == ()


def test_shared_finding_utility_preserves_fail_order_and_fields():
    first_evidence = (
        Evidence(
            source="synthetic-source",
            sha256="a" * 64,
            line_number=None,
            content="synthetic evidence one",
        ),
    )
    second_evidence = (
        Evidence(
            source="synthetic-source",
            sha256="b" * 64,
            line_number=None,
            content="synthetic evidence two",
        ),
    )
    first = RuleEvaluation(
        rule_id="IOS-TEST-001",
        rule_name="First rule",
        status=RuleStatus.FAIL,
        severity=Severity.HIGH,
        message="First message",
        recommendation="First recommendation",
        evidence=first_evidence,
    )
    ignored = _evaluation("IOS-TEST-002", RuleStatus.PASS)
    second = RuleEvaluation(
        rule_id="IOS-TEST-003",
        rule_name="Second rule",
        status=RuleStatus.FAIL,
        severity=Severity.LOW,
        message="Second message",
        recommendation="Second recommendation",
        evidence=second_evidence,
    )

    findings = findings_from_evaluations((first, ignored, second))

    assert isinstance(findings, tuple)
    assert tuple(finding.rule_id for finding in findings) == (
        first.rule_id,
        second.rule_id,
    )
    assert findings[0].rule_name == first.rule_name
    assert findings[0].severity is first.severity
    assert findings[0].message == first.message
    assert findings[0].recommendation == first.recommendation
    assert findings[0].evidence is first.evidence
    assert findings[1].evidence is second.evidence


def test_rejects_input_that_is_not_a_validated_batch(monkeypatch):
    analyzer = MagicMock()
    monkeypatch.setattr(service_module, "analyze_bytes", analyzer)

    with pytest.raises(TypeError, match="lote validado"):
        analyze_validated_evidence_batch(object())

    analyzer.assert_not_called()


def test_rejects_configuration_result_with_inconsistent_hash_safely(
    wired_flow,
):
    batch = wired_flow["batch"]
    sensitive_output = batch.evidence_for("show running-config").raw_output
    wired_flow["analyzer"].return_value = AnalysisResult(
        source_path="safe-source",
        sha256="0" * 64,
        evaluations=(),
        findings=(),
    )

    with pytest.raises(FullDeviceAnalysisContractError) as captured:
        analyze_validated_evidence_batch(batch)

    assert sensitive_output not in str(captured.value)
    assert DEVICE not in str(captured.value)
    wired_flow["parser"].assert_not_called()


def test_rejects_crossed_operational_model_safely(wired_flow):
    batch = wired_flow["batch"]
    version_evidence = batch.evidence_for("show version")
    crossed_context = OperationalContext(
        execution_id=batch.execution_id,
        device_host=version_evidence.device_host,
        command="show version",
        collected_at=version_evidence.collected_at,
        sha256=version_evidence.sha256,
        data=ShowIpSshData(True, "2.0", 120, 3),
    )
    wired_flow["parser"].side_effect = (
        lambda evidence: crossed_context
        if evidence.command == "show version"
        else wired_flow["operational_contexts"][evidence.command]
    )

    with pytest.raises(FullDeviceAnalysisContractError) as captured:
        analyze_validated_evidence_batch(batch)

    assert version_evidence.raw_output not in str(captured.value)
    assert DEVICE not in str(captured.value)
    wired_flow["rule"].evaluate.assert_not_called()


def test_rejects_incompatible_operational_evaluation_safely(wired_flow):
    wired_flow["rule"].evaluate.return_value = object()

    with pytest.raises(FullDeviceAnalysisContractError) as captured:
        analyze_validated_evidence_batch(wired_flow["batch"])

    assert DEVICE not in str(captured.value)
    wired_flow["finding_builder"].assert_not_called()


def test_configuration_error_propagates_without_partial_result(
    wired_flow,
    monkeypatch,
):
    error = AnalysisError("No fue posible analizar la configuración.")
    result_factory = MagicMock()
    wired_flow["analyzer"].side_effect = error
    monkeypatch.setattr(service_module, "FullDeviceAnalysisResult", result_factory)

    with pytest.raises(AnalysisError) as captured:
        analyze_validated_evidence_batch(wired_flow["batch"])

    assert captured.value is error
    wired_flow["parser"].assert_not_called()
    result_factory.assert_not_called()


def test_operational_error_propagates_without_partial_result(
    wired_flow,
    monkeypatch,
):
    error = OperationalAnalysisError(
        "No fue posible estructurar la evidencia operacional."
    )
    result_factory = MagicMock()
    wired_flow["parser"].side_effect = error
    monkeypatch.setattr(service_module, "FullDeviceAnalysisResult", result_factory)

    with pytest.raises(OperationalAnalysisError) as captured:
        analyze_validated_evidence_batch(wired_flow["batch"])

    assert captured.value is error
    wired_flow["rule"].evaluate.assert_not_called()
    result_factory.assert_not_called()


def test_orchestration_does_not_modify_batch_or_evidences(wired_flow):
    batch = wired_flow["batch"]
    original_batch = (batch.execution_id, batch.evidences)
    original_evidence_values = tuple(
        tuple(getattr(evidence, field.name) for field in fields(evidence))
        for evidence in batch.evidences
    )

    analyze_validated_evidence_batch(batch)

    assert (batch.execution_id, batch.evidences) == original_batch
    assert original_evidence_values == tuple(
        tuple(getattr(evidence, field.name) for field in fields(evidence))
        for evidence in batch.evidences
    )


def test_service_imports_no_collector_or_network_objects():
    assert "CommandEvidence" not in service_module.__dict__
    assert "NetmikoCollector" not in service_module.__dict__
    assert "ConnectHandler" not in service_module.__dict__
    assert "socket" not in service_module.__dict__
    assert "CommandEvidence" not in rule_results_module.__dict__
    assert "NetmikoCollector" not in rule_results_module.__dict__
    assert "ConnectHandler" not in rule_results_module.__dict__


def test_real_pure_flow_executes_existing_parsers_and_rules():
    batch = _batch()

    result = analyze_validated_evidence_batch(batch)

    assert result.execution_id == batch.execution_id
    assert len(result.configuration_evaluations) == 3
    assert len(result.operational_results) == 3
    assert tuple(context.command for context in result.operational_results) == (
        "show version",
        "show ip interface brief",
        "show ip ssh",
    )
    assert len(result.operational_evaluations) == 1
    assert result.operational_evaluations[0].rule_id == "IOS-IF-001"
    assert result.operational_evaluations[0].status is RuleStatus.FAIL
    assert len(result.configuration_findings) == 0
    assert len(result.operational_findings) == 1
    assert len(result.evaluations) == 4
    assert len(result.findings) == 1
