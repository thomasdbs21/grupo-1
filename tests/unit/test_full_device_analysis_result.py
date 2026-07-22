from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from ios_auditor.collectors import CommandEvidence
from ios_auditor.domain import (
    AnalysisResult,
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


def _evaluation(rule_id: str, status: RuleStatus) -> RuleEvaluation:
    return RuleEvaluation(
        rule_id=rule_id,
        rule_name=f"Rule {rule_id}",
        status=status,
        severity=Severity.MEDIUM,
        message="Resultado técnico de prueba.",
        recommendation="Recomendación técnica de prueba.",
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


def _evidence(execution_id: UUID, command: str, marker: str) -> CommandEvidence:
    return CommandEvidence(
        execution_id=execution_id,
        device_host="<REDACTED>",
        command=command,
        collected_at=datetime.now(timezone.utc),
        raw_output=marker,
        normalized_output=marker,
        sha256=marker * 64,
    )


def _operational_result(
    execution_id: UUID,
    command: str,
    data: ShowVersionData | ShowIpInterfaceBriefData | ShowIpSshData,
) -> OperationalContext:
    return OperationalContext(
        execution_id=execution_id,
        device_host="<REDACTED>",
        command=command,
        collected_at=datetime.now(timezone.utc),
        sha256="a" * 64,
        data=data,
    )


@pytest.fixture
def integral_parts():
    execution_id = uuid4()
    evidences = (
        _evidence(execution_id, "show running-config", "a"),
        _evidence(execution_id, "show version", "b"),
        _evidence(execution_id, "show ip interface brief", "c"),
        _evidence(execution_id, "show ip ssh", "d"),
    )
    config_fail = _evaluation("IOS-ADM-001", RuleStatus.FAIL)
    configuration_result = AnalysisResult(
        source_path="<REDACTED>",
        sha256="a" * 64,
        evaluations=(config_fail,),
        findings=(_finding(config_fail),),
    )
    operational_results = (
        _operational_result(
            execution_id,
            "show version",
            ShowVersionData("test-version", None, None, None),
        ),
        _operational_result(
            execution_id,
            "show ip interface brief",
            ShowIpInterfaceBriefData(interfaces=()),
        ),
        _operational_result(
            execution_id,
            "show ip ssh",
            ShowIpSshData(False, None, None, None),
        ),
    )
    operational_fail = _evaluation("IOS-IF-001", RuleStatus.FAIL)
    return {
        "execution_id": execution_id,
        "evidences": evidences,
        "configuration_result": configuration_result,
        "operational_results": operational_results,
        "operational_evaluations": (operational_fail,),
        "operational_findings": (_finding(operational_fail),),
    }


def test_valid_result_preserves_composed_objects(integral_parts):
    result = FullDeviceAnalysisResult(**integral_parts)

    assert isinstance(result.execution_id, UUID)
    assert result.execution_id is integral_parts["execution_id"]
    assert result.configuration_result is integral_parts["configuration_result"]
    assert all(
        actual is original
        for actual, original in zip(
            result.evidences, integral_parts["evidences"], strict=True
        )
    )
    assert all(
        actual is original
        for actual, original in zip(
            result.operational_results,
            integral_parts["operational_results"],
            strict=True,
        )
    )


def test_evaluations_and_findings_are_aggregated_without_copying(integral_parts):
    result = FullDeviceAnalysisResult(**integral_parts)

    assert result.configuration_evaluations is result.configuration_result.evaluations
    assert result.configuration_findings is result.configuration_result.findings
    assert result.evaluations == (
        result.configuration_evaluations + result.operational_evaluations
    )
    assert result.findings == (
        result.configuration_findings + result.operational_findings
    )
    assert (
        result.evaluations[0]
        is integral_parts["configuration_result"].evaluations[0]
    )
    assert result.evaluations[1] is integral_parts["operational_evaluations"][0]
    assert result.findings[0] is integral_parts["configuration_result"].findings[0]
    assert result.findings[1] is integral_parts["operational_findings"][0]


@pytest.mark.parametrize(
    "status",
    [
        RuleStatus.PASS,
        RuleStatus.NOT_APPLICABLE,
        RuleStatus.NOT_EVALUATED,
        RuleStatus.ERROR,
    ],
)
def test_non_fail_operational_evaluations_have_no_findings(integral_parts, status):
    evaluation = _evaluation("IOS-IF-001", status)
    integral_parts["operational_evaluations"] = (evaluation,)
    integral_parts["operational_findings"] = ()

    result = FullDeviceAnalysisResult(**integral_parts)

    assert result.operational_findings == ()
    assert all(finding.rule_id != evaluation.rule_id for finding in result.findings)


def test_inconsistent_operational_findings_are_rejected(integral_parts):
    passing = _evaluation("IOS-IF-001", RuleStatus.PASS)
    integral_parts["operational_evaluations"] = (passing,)
    integral_parts["operational_findings"] = (_finding(passing),)

    with pytest.raises(ValueError, match="evaluaciones FAIL"):
        FullDeviceAnalysisResult(**integral_parts)


def test_missing_finding_for_fail_is_rejected(integral_parts):
    integral_parts["operational_findings"] = ()

    with pytest.raises(ValueError, match="evaluaciones FAIL"):
        FullDeviceAnalysisResult(**integral_parts)


def test_duplicated_finding_is_rejected(integral_parts):
    finding = integral_parts["operational_findings"][0]
    integral_parts["operational_findings"] = (finding, finding)

    with pytest.raises(ValueError, match="evaluaciones FAIL"):
        FullDeviceAnalysisResult(**integral_parts)


def test_additional_finding_is_rejected(integral_parts):
    additional_evaluation = _evaluation("IOS-EXTRA-001", RuleStatus.FAIL)
    integral_parts["operational_findings"] += (_finding(additional_evaluation),)

    with pytest.raises(ValueError, match="evaluaciones FAIL"):
        FullDeviceAnalysisResult(**integral_parts)


def test_inconsistent_configuration_findings_are_rejected(integral_parts):
    config_pass = _evaluation("IOS-ADM-001", RuleStatus.PASS)
    integral_parts["configuration_result"] = AnalysisResult(
        source_path="<REDACTED>",
        sha256="a" * 64,
        evaluations=(config_pass,),
        findings=(_finding(config_pass),),
    )

    with pytest.raises(ValueError, match="evaluaciones FAIL"):
        FullDeviceAnalysisResult(**integral_parts)


def test_result_and_all_exposed_collections_are_immutable(integral_parts):
    integral_parts["evidences"] = list(integral_parts["evidences"])
    integral_parts["operational_results"] = list(
        integral_parts["operational_results"]
    )
    integral_parts["operational_evaluations"] = list(
        integral_parts["operational_evaluations"]
    )
    integral_parts["operational_findings"] = list(
        integral_parts["operational_findings"]
    )

    result = FullDeviceAnalysisResult(**integral_parts)

    assert isinstance(result.evidences, tuple)
    assert isinstance(result.operational_results, tuple)
    assert isinstance(result.configuration_evaluations, tuple)
    assert isinstance(result.operational_evaluations, tuple)
    assert isinstance(result.evaluations, tuple)
    assert isinstance(result.configuration_findings, tuple)
    assert isinstance(result.operational_findings, tuple)
    assert isinstance(result.findings, tuple)
    with pytest.raises(FrozenInstanceError):
        result.execution_id = uuid4()


def test_execution_id_must_be_uuid(integral_parts):
    integral_parts["execution_id"] = "not-a-uuid"

    with pytest.raises(TypeError, match="UUID"):
        FullDeviceAnalysisResult(**integral_parts)


def test_domain_contract_does_not_import_infrastructure_at_runtime():
    import ios_auditor.domain.full_device as module

    assert "CommandEvidence" not in module.__dict__
    assert "NetmikoCollector" not in module.__dict__
    assert "ConnectHandler" not in module.__dict__
