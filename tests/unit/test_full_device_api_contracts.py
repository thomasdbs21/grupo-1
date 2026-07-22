from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from ios_auditor.api.full_device_serialization import (
    FullDeviceResponseContractError,
    to_full_device_analysis_response,
)
from ios_auditor.api.schemas import DeviceAnalysisRequest
from ios_auditor.collectors import CommandEvidence
from ios_auditor.domain import (
    AnalysisResult,
    Evidence,
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
from ios_auditor.services import CANONICAL_EVIDENCE_COMMANDS
from ios_auditor.services.rule_results import findings_from_evaluations


VALID_REQUEST = {
    "host": "192.168.50.10",
    "port": 22,
    "username": "synthetic-user",
    "password": "SYNTHETIC_PASSWORD_VALUE",
}
SENSITIVE_HOST = "device.example.invalid"
SENSITIVE_RAW_MARKER = "SYNTHETIC_RAW_OUTPUT_DO_NOT_EXPOSE"


def _evaluation(
    rule_id: str,
    status: RuleStatus,
    severity: Severity,
) -> RuleEvaluation:
    evidence = (
        Evidence(
            source="synthetic-source",
            sha256="e" * 64,
            line_number=1,
            content="enable password <REDACTED>",
        ),
    )
    return RuleEvaluation(
        rule_id=rule_id,
        rule_name=f"Synthetic rule {rule_id}",
        status=status,
        severity=severity,
        message="Synthetic technical result.",
        recommendation="Synthetic safe recommendation.",
        evidence=evidence,
    )


def _full_result(*, additional_evaluation: bool = False) -> FullDeviceAnalysisResult:
    execution_id = uuid4()
    collected_at = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
    evidences = tuple(
        CommandEvidence(
            execution_id=execution_id,
            device_host=SENSITIVE_HOST,
            command=command,
            collected_at=collected_at,
            raw_output=f"{SENSITIVE_RAW_MARKER}:{command}\r\n",
            normalized_output=f"{SENSITIVE_RAW_MARKER}:{command}\n",
            sha256=hashlib.sha256(
                f"{SENSITIVE_RAW_MARKER}:{command}\r\n".encode("utf-8")
            ).hexdigest(),
        )
        for command in CANONICAL_EVIDENCE_COMMANDS
    )
    configuration_evaluations = (
        _evaluation("IOS-ADM-001", RuleStatus.PASS, Severity.HIGH),
        _evaluation("IOS-SRV-001", RuleStatus.FAIL, Severity.MEDIUM),
        _evaluation("IOS-AUTH-001", RuleStatus.NOT_APPLICABLE, Severity.HIGH),
    )
    if additional_evaluation:
        configuration_evaluations += (
            _evaluation("IOS-FUTURE-001", RuleStatus.ERROR, Severity.CRITICAL),
        )
    configuration_result = AnalysisResult(
        source_path="synthetic-running-config",
        sha256=evidences[0].sha256,
        evaluations=configuration_evaluations,
        findings=findings_from_evaluations(configuration_evaluations),
    )
    operational_results = (
        OperationalContext(
            execution_id=execution_id,
            device_host=SENSITIVE_HOST,
            command="show version",
            collected_at=collected_at,
            sha256=evidences[1].sha256,
            data=ShowVersionData("synthetic-version", None, None, None),
        ),
        OperationalContext(
            execution_id=execution_id,
            device_host=SENSITIVE_HOST,
            command="show ip interface brief",
            collected_at=collected_at,
            sha256=evidences[2].sha256,
            data=ShowIpInterfaceBriefData(interfaces=()),
        ),
        OperationalContext(
            execution_id=execution_id,
            device_host=SENSITIVE_HOST,
            command="show ip ssh",
            collected_at=collected_at,
            sha256=evidences[3].sha256,
            data=ShowIpSshData(True, "2.0", 120, 3),
        ),
    )
    operational_evaluations = (
        _evaluation("IOS-IF-001", RuleStatus.NOT_EVALUATED, Severity.MEDIUM),
    )
    return FullDeviceAnalysisResult(
        execution_id=execution_id,
        evidences=evidences,
        configuration_result=configuration_result,
        operational_results=operational_results,
        operational_evaluations=operational_evaluations,
        operational_findings=findings_from_evaluations(operational_evaluations),
    )


def test_valid_device_analysis_request_masks_password():
    request = DeviceAnalysisRequest(**VALID_REQUEST)

    assert str(request.host) == VALID_REQUEST["host"]
    assert request.port == 22
    assert request.username == VALID_REQUEST["username"]
    assert request.password.get_secret_value() == VALID_REQUEST["password"]
    assert VALID_REQUEST["password"] not in repr(request)
    assert VALID_REQUEST["password"] not in request.model_dump_json()


@pytest.mark.parametrize("host", ("10.0.0.1", "172.16.0.1", "192.168.0.1"))
def test_accepts_each_rfc1918_range(host):
    request = DeviceAnalysisRequest(**{**VALID_REQUEST, "host": host})

    assert str(request.host) == host


@pytest.mark.parametrize(
    "host",
    (
        "router.example.invalid",
        "2001:db8::1",
        "203.0.113.10",
        "127.0.0.1",
        "169.254.1.1",
        "224.0.0.1",
        "0.0.0.0",
        "240.0.0.1",
        "10.0.0.0",
        "10.255.255.255",
        "172.16.0.0",
        "172.31.255.255",
        "192.168.0.0",
        "192.168.1.255",
        "192.168.255.255",
    ),
)
def test_rejects_ipv4_destinations_outside_conservative_mvp_policy(host):
    with pytest.raises(ValidationError):
        DeviceAnalysisRequest(**{**VALID_REQUEST, "host": host})


@pytest.mark.parametrize("port", (0, -1, 65536))
def test_rejects_invalid_ports(port):
    with pytest.raises(ValidationError):
        DeviceAnalysisRequest(**{**VALID_REQUEST, "port": port})


@pytest.mark.parametrize("username", ("", "synthetic\nuser", " synthetic-user"))
def test_rejects_invalid_usernames(username):
    with pytest.raises(ValidationError):
        DeviceAnalysisRequest(**{**VALID_REQUEST, "username": username})


def test_rejects_empty_password():
    with pytest.raises(ValidationError):
        DeviceAnalysisRequest(**{**VALID_REQUEST, "password": ""})


@pytest.mark.parametrize("field", ("command", "commands", "timeout", "other"))
def test_rejects_additional_fields(field):
    with pytest.raises(ValidationError):
        DeviceAnalysisRequest(**{**VALID_REQUEST, field: "synthetic"})


def test_pydantic_validation_error_retains_invalid_secret_input():
    invalid_secret = "SYNTHETIC_INVALID_SECRET_" + "x" * 1024

    with pytest.raises(ValidationError) as captured:
        DeviceAnalysisRequest(**{**VALID_REQUEST, "password": invalid_secret})

    assert any(
        error.get("input") == invalid_secret for error in captured.value.errors()
    )


def test_transforms_full_result_to_explicit_safe_contract():
    result = _full_result()

    response = to_full_device_analysis_response(result)

    assert response.execution_id == result.execution_id
    assert isinstance(response.execution_id, UUID)
    assert [item.command for item in response.evidences] == list(
        CANONICAL_EVIDENCE_COMMANDS
    )
    assert [item.raw_output_sha256 for item in response.evidences] == [
        evidence.sha256 for evidence in result.evidences
    ]
    assert all(
        item.collected_at == evidence.collected_at
        for item, evidence in zip(response.evidences, result.evidences, strict=True)
    )
    assert response.operational_context_count == 3
    assert response.total_evaluations == len(result.evaluations) == 4
    assert response.total_findings == len(result.findings) == 1
    assert [item.rule_id for item in response.rule_evaluations] == [
        evaluation.rule_id for evaluation in result.evaluations
    ]
    assert [item.rule_id for item in response.findings] == ["IOS-SRV-001"]


def test_response_summaries_use_real_enums_and_exact_counts():
    response = to_full_device_analysis_response(_full_result())

    assert response.status_summary == {
        RuleStatus.PASS: 1,
        RuleStatus.FAIL: 1,
        RuleStatus.NOT_APPLICABLE: 1,
        RuleStatus.NOT_EVALUATED: 1,
    }
    assert response.finding_severity_summary == {Severity.MEDIUM: 1}


def test_response_json_excludes_sensitive_and_complete_internal_data():
    response = to_full_device_analysis_response(_full_result())

    payload = response.model_dump_json()
    parsed = json.loads(payload)

    assert parsed["operational_context_count"] == 3
    assert set(parsed["evidences"][0]) == {
        "command",
        "collected_at",
        "raw_output_sha256",
    }
    for forbidden in (
        SENSITIVE_HOST,
        VALID_REQUEST["username"],
        VALID_REQUEST["password"],
        SENSITIVE_RAW_MARKER,
        "normalized_output",
        "device_host",
        "operational_results",
        "configuration_result",
    ):
        assert forbidden not in payload


def test_transformer_preserves_future_additional_evaluations():
    result = _full_result(additional_evaluation=True)

    response = to_full_device_analysis_response(result)

    assert response.total_evaluations == 5
    assert "IOS-FUTURE-001" in {
        evaluation.rule_id for evaluation in response.rule_evaluations
    }
    assert response.status_summary[RuleStatus.ERROR] == 1
    assert response.total_findings == 1


def test_transformer_rejects_mismatched_execution_id_safely():
    result = _full_result()
    crossed = replace(result.evidences[0], execution_id=uuid4())
    invalid_result = replace(result, evidences=(crossed, *result.evidences[1:]))

    with pytest.raises(FullDeviceResponseContractError) as captured:
        to_full_device_analysis_response(invalid_result)

    message = str(captured.value)
    assert SENSITIVE_HOST not in message
    assert SENSITIVE_RAW_MARKER not in message


def test_transformer_rejects_non_canonical_evidence_set_safely():
    result = _full_result()
    invalid_result = replace(result, evidences=result.evidences[:-1])

    with pytest.raises(FullDeviceResponseContractError) as captured:
        to_full_device_analysis_response(invalid_result)

    assert SENSITIVE_HOST not in str(captured.value)
    assert SENSITIVE_RAW_MARKER not in str(captured.value)
