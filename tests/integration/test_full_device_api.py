from __future__ import annotations

import json
import logging
from dataclasses import replace
from unittest.mock import MagicMock, call

import pytest
from fastapi.testclient import TestClient

import ios_auditor.api.app as app_module
from ios_auditor.api.app import (
    DEVICE_ANALYSIS_FAILED_CODE,
    DEVICE_ANALYSIS_FAILED_MESSAGE,
    DEVICE_TIMEOUT_CODE,
    DEVICE_TIMEOUT_MESSAGE,
    INTERNAL_ERROR_MESSAGE,
    app,
)
from ios_auditor.api.dependencies import get_connection_factory
from ios_auditor.api.full_device_serialization import (
    FullDeviceResponseContractError,
)
from ios_auditor.api.schemas import FullDeviceAnalysisResponse
from ios_auditor.collectors import (
    CollectorAuthenticationError,
    CollectorConnectionError,
    CollectorTimeoutError,
    CommandNotAllowedError,
)
from ios_auditor.domain import RuleEvaluation, RuleStatus, Severity
from ios_auditor.services import (
    AnalysisError,
    CANONICAL_EVIDENCE_COMMANDS,
    EvidenceBatchValidationError,
    FullDeviceAnalysisContractError,
    OperationalAnalysisError,
)


DEVICE_ENDPOINT = "/api/v1/device-analyses"
SYNTHETIC_HOST = "192.168.50.10"
SYNTHETIC_USERNAME = "synthetic-user"
SYNTHETIC_PASSWORD = "SYNTHETIC_PASSWORD_NOT_REAL"
SENSITIVE_ERROR_MARKER = "SYNTHETIC_INTERNAL_VALUE_NOT_TO_EXPOSE"
VALID_REQUEST = {
    "host": SYNTHETIC_HOST,
    "port": 22,
    "username": SYNTHETIC_USERNAME,
    "password": SYNTHETIC_PASSWORD,
}
RAW_OUTPUTS = {
    "show running-config": (
        "line vty 0 4\r\n"
        " transport input ssh\r\n"
        "ip http secure-server\r\n"
    ),
    "show version": "Cisco IOS XE Software, Version 16.09.05\r\n",
    "show ip interface brief": (
        "Interface IP-Address OK? Method Status Protocol\r\n"
        "GigabitEthernet1 unassigned YES unset up down\r\n"
    ),
    "show ip ssh": (
        "SSH Enabled - version 2.0\r\n"
        "Authentication timeout: 120 secs; Authentication retries: 3\r\n"
    ),
}


@pytest.fixture
def connection() -> MagicMock:
    connection = MagicMock()
    connection.send_command.side_effect = lambda command: RAW_OUTPUTS[command]
    return connection


@pytest.fixture
def connection_factory(connection) -> MagicMock:
    return MagicMock(return_value=connection)


@pytest.fixture
def client(connection_factory):
    app.dependency_overrides[get_connection_factory] = lambda: connection_factory
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def _post(client: TestClient, payload: dict | None = None):
    return client.post(DEVICE_ENDPOINT, json=payload or VALID_REQUEST)


def _assert_public_error(response, status_code: int, code: str, message: str):
    assert response.status_code == status_code
    assert response.json() == {"error": {"code": code, "message": message}}
    for forbidden in (
        SYNTHETIC_HOST,
        SYNTHETIC_USERNAME,
        SYNTHETIC_PASSWORD,
        SENSITIVE_ERROR_MARKER,
        "Traceback",
    ):
        assert forbidden not in response.text


def test_post_runs_integral_service_once_and_uses_safe_transformer(
    client,
    connection_factory,
    connection,
    monkeypatch,
):
    real_service = app_module.collect_and_analyze_device
    real_transformer = app_module.to_full_device_analysis_response
    service_spy = MagicMock(side_effect=real_service)
    transformer_spy = MagicMock(side_effect=real_transformer)
    monkeypatch.setattr(app_module, "collect_and_analyze_device", service_spy)
    monkeypatch.setattr(
        app_module,
        "to_full_device_analysis_response",
        transformer_spy,
    )

    response = _post(client)

    assert response.status_code == 200
    FullDeviceAnalysisResponse.model_validate(response.json())
    service_spy.assert_called_once_with(
        host=SYNTHETIC_HOST,
        port=22,
        username=SYNTHETIC_USERNAME,
        password=SYNTHETIC_PASSWORD,
        connection_factory=connection_factory,
    )
    transformer_spy.assert_called_once()
    connection_factory.assert_called_once_with(
        device_type="cisco_ios",
        host=SYNTHETIC_HOST,
        port=22,
        username=SYNTHETIC_USERNAME,
        password=SYNTHETIC_PASSWORD,
    )
    assert connection.send_command.call_args_list == [
        call(command) for command in CANONICAL_EVIDENCE_COMMANDS
    ]
    connection.disconnect.assert_called_once_with()
    connection.send_config_set.assert_not_called()
    connection.config_mode.assert_not_called()
    connection.enable.assert_not_called()


def test_success_response_contains_only_authorized_integral_data(client):
    response = _post(client)
    body = response.json()

    assert response.status_code == 200
    assert body["execution_id"]
    assert [item["command"] for item in body["evidences"]] == list(
        CANONICAL_EVIDENCE_COMMANDS
    )
    assert all(
        set(item) == {"command", "collected_at", "raw_output_sha256"}
        for item in body["evidences"]
    )
    assert body["operational_context_count"] == 3
    assert body["total_evaluations"] == 4
    assert body["total_findings"] == 1
    assert len(body["rule_evaluations"]) == body["total_evaluations"]
    assert len(body["findings"]) == body["total_findings"]
    assert body["status_summary"] == {
        "PASS": 2,
        "NOT_APPLICABLE": 1,
        "FAIL": 1,
    }
    assert body["finding_severity_summary"] == {"MEDIUM": 1}
    serialized = response.text
    for forbidden in (
        SYNTHETIC_HOST,
        SYNTHETIC_USERNAME,
        SYNTHETIC_PASSWORD,
        "device_host",
        "raw_output\"",
        "normalized_output",
        "configuration_result",
        "operational_results",
        RAW_OUTPUTS["show running-config"],
    ):
        assert forbidden not in serialized


def test_non_post_method_does_not_create_connection(client, connection_factory):
    response = client.get(DEVICE_ENDPOINT)

    assert response.status_code == 405
    connection_factory.assert_not_called()


@pytest.mark.parametrize(
    ("replacement", "sensitive_value"),
    (
        ({"host": "router.example.invalid"}, "router.example.invalid"),
        ({"host": "203.0.113.10"}, "203.0.113.10"),
        ({"host": "2001:db8::1"}, "2001:db8::1"),
        ({"host": "127.0.0.1"}, "127.0.0.1"),
        ({"port": 0}, "0"),
        ({"username": "synthetic\nuser"}, "synthetic"),
        ({"password": ""}, None),
        (
            {"password": "SYNTHETIC_TOO_LONG_SECRET_" + "x" * 1024},
            "SYNTHETIC_TOO_LONG_SECRET_",
        ),
        (
            {"commands": "SYNTHETIC_UNTRUSTED_COMMAND_VALUE"},
            "SYNTHETIC_UNTRUSTED_COMMAND_VALUE",
        ),
        (
            {"command": "SYNTHETIC_UNTRUSTED_COMMAND_VALUE"},
            "SYNTHETIC_UNTRUSTED_COMMAND_VALUE",
        ),
        ({"timeout": "SYNTHETIC_UNTRUSTED_TIMEOUT"}, "SYNTHETIC_UNTRUSTED_TIMEOUT"),
        (
            {"device_type": "SYNTHETIC_UNTRUSTED_DEVICE_TYPE"},
            "SYNTHETIC_UNTRUSTED_DEVICE_TYPE",
        ),
    ),
)
def test_invalid_request_returns_fully_sanitized_422(
    client,
    connection_factory,
    replacement,
    sensitive_value,
):
    payload = {**VALID_REQUEST, **replacement}

    response = _post(client, payload)

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "INVALID_REQUEST",
            "message": "La solicitud no es válida.",
        }
    }
    serialized = response.text
    if sensitive_value:
        assert sensitive_value not in serialized
    for forbidden in (
        SYNTHETIC_HOST,
        SYNTHETIC_USERNAME,
        SYNTHETIC_PASSWORD,
        "input",
        "ctx",
        "body",
        "commands",
    ):
        assert forbidden not in serialized
    connection_factory.assert_not_called()


@pytest.mark.parametrize(
    ("error", "status_code", "code", "message"),
    (
        (
            CollectorTimeoutError(SENSITIVE_ERROR_MARKER),
            504,
            DEVICE_TIMEOUT_CODE,
            DEVICE_TIMEOUT_MESSAGE,
        ),
        (
            CollectorAuthenticationError(SENSITIVE_ERROR_MARKER),
            502,
            DEVICE_ANALYSIS_FAILED_CODE,
            DEVICE_ANALYSIS_FAILED_MESSAGE,
        ),
        (
            CollectorConnectionError(SENSITIVE_ERROR_MARKER),
            502,
            DEVICE_ANALYSIS_FAILED_CODE,
            DEVICE_ANALYSIS_FAILED_MESSAGE,
        ),
        (
            CollectorConnectionError(
                f"command failure {SENSITIVE_ERROR_MARKER} show running-config"
            ),
            502,
            DEVICE_ANALYSIS_FAILED_CODE,
            DEVICE_ANALYSIS_FAILED_MESSAGE,
        ),
        (
            EvidenceBatchValidationError("SYNTHETIC", SENSITIVE_ERROR_MARKER),
            502,
            DEVICE_ANALYSIS_FAILED_CODE,
            DEVICE_ANALYSIS_FAILED_MESSAGE,
        ),
        (
            OperationalAnalysisError(SENSITIVE_ERROR_MARKER),
            502,
            DEVICE_ANALYSIS_FAILED_CODE,
            DEVICE_ANALYSIS_FAILED_MESSAGE,
        ),
        (
            AnalysisError(SENSITIVE_ERROR_MARKER),
            502,
            DEVICE_ANALYSIS_FAILED_CODE,
            DEVICE_ANALYSIS_FAILED_MESSAGE,
        ),
        (
            CommandNotAllowedError(SENSITIVE_ERROR_MARKER),
            500,
            "INTERNAL_ERROR",
            INTERNAL_ERROR_MESSAGE,
        ),
        (
            FullDeviceAnalysisContractError(SENSITIVE_ERROR_MARKER),
            500,
            "INTERNAL_ERROR",
            INTERNAL_ERROR_MESSAGE,
        ),
        (
            RuntimeError(SENSITIVE_ERROR_MARKER),
            500,
            "INTERNAL_ERROR",
            INTERNAL_ERROR_MESSAGE,
        ),
    ),
)
def test_service_errors_are_mapped_by_class_without_exposing_details(
    client,
    monkeypatch,
    error,
    status_code,
    code,
    message,
):
    service = MagicMock(side_effect=error)
    monkeypatch.setattr(app_module, "collect_and_analyze_device", service)

    response = _post(client)

    service.assert_called_once()
    _assert_public_error(response, status_code, code, message)
    assert "show running-config" not in response.text


def test_transformer_error_returns_sanitized_500(client, monkeypatch):
    service = MagicMock(return_value=object())
    transformer = MagicMock(
        side_effect=FullDeviceResponseContractError(SENSITIVE_ERROR_MARKER)
    )
    monkeypatch.setattr(app_module, "collect_and_analyze_device", service)
    monkeypatch.setattr(app_module, "to_full_device_analysis_response", transformer)

    response = _post(client)

    service.assert_called_once()
    transformer.assert_called_once_with(service.return_value)
    _assert_public_error(response, 500, "INTERNAL_ERROR", INTERNAL_ERROR_MESSAGE)


def test_endpoint_preserves_future_additional_evaluations(client, monkeypatch):
    real_service = app_module.collect_and_analyze_device

    def service_with_additional_evaluation(**kwargs):
        result = real_service(**kwargs)
        additional = RuleEvaluation(
            rule_id="IOS-FUTURE-001",
            rule_name="Synthetic future rule",
            status=RuleStatus.ERROR,
            severity=Severity.CRITICAL,
            message="Synthetic technical result.",
            recommendation="Synthetic safe recommendation.",
        )
        configuration_result = replace(
            result.configuration_result,
            evaluations=(*result.configuration_evaluations, additional),
        )
        return replace(result, configuration_result=configuration_result)

    monkeypatch.setattr(
        app_module,
        "collect_and_analyze_device",
        service_with_additional_evaluation,
    )

    response = _post(client)

    assert response.status_code == 200
    assert response.json()["total_evaluations"] == 5
    assert response.json()["rule_evaluations"][-2]["rule_id"] == "IOS-FUTURE-001"
    assert response.json()["status_summary"]["ERROR"] == 1
    assert response.json()["total_findings"] == 1


def test_request_logging_never_contains_connection_parameters(client, caplog):
    with caplog.at_level(logging.INFO, logger="ios_auditor.api"):
        response = _post(client)

    assert response.status_code == 200
    assert DEVICE_ENDPOINT in caplog.text
    assert SYNTHETIC_HOST not in caplog.text
    assert SYNTHETIC_USERNAME not in caplog.text
    assert SYNTHETIC_PASSWORD not in caplog.text


def test_unexpected_dependency_error_is_not_logged_or_returned(
    client,
    caplog,
):
    def failing_dependency():
        raise RuntimeError(
            f"{SENSITIVE_ERROR_MARKER} {SYNTHETIC_HOST} "
            f"{SYNTHETIC_USERNAME} {SYNTHETIC_PASSWORD}"
        )

    app.dependency_overrides[get_connection_factory] = failing_dependency

    with caplog.at_level(logging.ERROR, logger="ios_auditor.api"):
        response = _post(client)

    _assert_public_error(response, 500, "INTERNAL_ERROR", INTERNAL_ERROR_MESSAGE)
    assert "RuntimeError" in caplog.text
    assert SENSITIVE_ERROR_MARKER not in caplog.text
    assert SYNTHETIC_HOST not in caplog.text
    assert SYNTHETIC_USERNAME not in caplog.text
    assert SYNTHETIC_PASSWORD not in caplog.text


def test_password_is_unwrapped_only_at_service_boundary():
    source = app_module.create_device_analysis.__code__

    assert "get_secret_value" in source.co_names
    assert source.co_names.count("get_secret_value") == 1
    assert "model_dump" not in source.co_names
    assert "to_primitive" not in source.co_names


def test_openapi_declares_safe_device_analysis_contract():
    schema = app.openapi()
    operation = schema["paths"][DEVICE_ENDPOINT]["post"]

    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/DeviceAnalysisRequest"
    }
    assert operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/FullDeviceAnalysisResponse"}
    request_properties = schema["components"]["schemas"][
        "DeviceAnalysisRequest"
    ]["properties"]
    assert set(request_properties) == {"host", "port", "username", "password"}
    evidence_properties = schema["components"]["schemas"][
        "CommandEvidenceMetadataResponse"
    ]["properties"]
    assert set(evidence_properties) == {
        "command",
        "collected_at",
        "raw_output_sha256",
    }
    serialized_operation = json.dumps(operation)
    assert "normalized_output" not in serialized_operation
    assert "device_host" not in serialized_operation
    assert not any("command" in path for path in schema["paths"] if path != DEVICE_ENDPOINT)
