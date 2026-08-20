from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ios_auditor.api.app import MAX_UPLOAD_BYTES, app
from ios_auditor.api.dependencies import get_analysis_repository, get_rule_registry
from ios_auditor.api.repository import InMemoryAnalysisRepository
from ios_auditor.rules import get_default_registry
from ios_auditor.rules.registry import build_registry


ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "samples"


@pytest.fixture
def repository() -> InMemoryAnalysisRepository:
    return InMemoryAnalysisRepository(max_items=100)


@pytest.fixture
def client(repository):
    app.dependency_overrides[get_analysis_repository] = lambda: repository
    app.dependency_overrides[get_rule_registry] = get_default_registry
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _sample_bytes(filename: str) -> bytes:
    return (SAMPLES / filename).read_bytes()


def _post(client: TestClient, filename: str, content: bytes):
    return client.post(
        "/api/v1/analyses",
        files={"file": (filename, content, "application/octet-stream")},
    )


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ios-auditor",
        "version": "0.1.0",
    }


def test_rules_lists_only_enabled_rules(client):
    response = client.get("/api/v1/rules")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [
        "IOS-ADM-001",
        "IOS-SRV-001",
        "IOS-AUTH-001",
        "IOS-ADM-002",
        "IOS-SRV-002",
        "IOS-NTP-001",
        "IOS-LOG-001",
    ]
    assert "expected_id" not in response.text


def test_rules_excludes_disabled_rule(repository):
    metadata = tuple(
        replace(rule.metadata, enabled=False)
        if rule.metadata.id == "IOS-SRV-001"
        else rule.metadata
        for rule in get_default_registry().list_rules()
    )
    disabled_registry = build_registry(metadata)
    app.dependency_overrides[get_analysis_repository] = lambda: repository
    app.dependency_overrides[get_rule_registry] = lambda: disabled_registry
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/api/v1/rules")
    finally:
        app.dependency_overrides.clear()

    assert [item["id"] for item in response.json()] == [
        "IOS-ADM-001",
        "IOS-AUTH-001",
        "IOS-ADM-002",
        "IOS-SRV-002",
        "IOS-NTP-001",
        "IOS-LOG-001",
    ]


def test_post_incorrect_configuration(client):
    response = _post(
        client,
        "incorrecta.cfg",
        _sample_bytes("running_config_incorrecta.cfg"),
    )
    body = response.json()

    assert response.status_code == 201
    assert body["status"] == "COMPLETED"
    assert body["total_evaluations"] == 7
    assert body["total_findings"] == 5
    assert body["status_summary"] == {
        "FAIL": 5,
        "NOT_EVALUATED": 1,
        "PASS": 1,
    }


def test_post_correct_configuration(client):
    response = _post(
        client,
        "correcta.conf",
        _sample_bytes("running_config_correcta.cfg"),
    )
    body = response.json()

    assert response.status_code == 201
    assert body["total_evaluations"] == 7
    assert body["total_findings"] == 2
    assert body["status_summary"] == {
        "PASS": 4,
        "NOT_EVALUATED": 1,
        "FAIL": 2,
    }


def test_analysis_can_be_retrieved_with_evaluations_and_findings(client):
    created = _post(
        client,
        "running.cfg",
        _sample_bytes("running_config_incorrecta.cfg"),
    ).json()
    analysis_id = created["analysis_id"]

    complete = client.get(f"/api/v1/analyses/{analysis_id}")
    evaluations = client.get(f"/api/v1/analyses/{analysis_id}/evaluations")
    findings = client.get(f"/api/v1/analyses/{analysis_id}/findings")

    assert complete.status_code == 200
    assert complete.json() == created
    assert evaluations.status_code == 200
    assert len(evaluations.json()) == 7
    assert findings.status_code == 200
    assert len(findings.json()) == 5


def test_unknown_analysis_id_returns_404(client):
    response = client.get("/api/v1/analyses/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"


def test_invalid_analysis_id_is_controlled(client):
    response = client.get("/api/v1/analyses/not-a-uuid")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_ANALYSIS_ID"


def test_missing_file_is_controlled(client):
    response = client.post("/api/v1/analyses")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MISSING_FILE"


def test_empty_file_is_rejected(client):
    response = _post(client, "empty.cfg", b"")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_FILE"


def test_empty_filename_is_rejected(client):
    response = _post(client, "   ", b"hostname R1\n")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_FILENAME"


def test_invalid_extension_is_rejected(client):
    response = _post(client, "running.exe", b"hostname R1\n")
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "INVALID_EXTENSION"


def test_file_larger_than_two_mib_is_rejected(client, repository):
    response = _post(client, "large.cfg", b"a" * (MAX_UPLOAD_BYTES + 1))
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"
    assert len(repository) == 0


def test_invalid_utf8_is_rejected(client):
    response = _post(client, "invalid.cfg", b"\xff\xfe\xfa")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ENCODING"


def test_binary_content_is_rejected(client):
    response = _post(client, "binary.cfg", b"hostname\x00R1")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ENCODING"


def test_filename_path_is_reduced_to_basename(client):
    response = _post(client, "C:\\secret\\router.cfg", b"hostname R1\n")
    assert response.status_code == 201
    assert response.json()["source_name"] == "router.cfg"


def test_response_has_no_absolute_server_path_or_complete_config(client):
    raw = _sample_bytes("running_config_incorrecta.cfg")
    response = _post(client, "running.cfg", raw)
    serialized = response.text

    assert response.status_code == 201
    assert str(ROOT) not in serialized
    assert raw.decode("utf-8") not in serialized
    assert "original_content" not in serialized
    assert "source_path" not in serialized


def test_enable_password_is_redacted(client):
    response = _post(
        client,
        "running.txt",
        b"enable password SUPER_SECRET_VALUE\n",
    )
    serialized = response.text

    assert response.status_code == 201
    assert "SUPER_SECRET_VALUE" not in serialized
    assert "<REDACTED>" in response.json()["findings"][0]["evidence"][0]["content"]


def test_utf8_bom_is_accepted(client):
    response = _post(
        client,
        "bom.cfg",
        b"\xef\xbb\xbfhostname R1\nline vty 0 4\n transport input ssh\n",
    )
    assert response.status_code == 201


def test_api_response_is_json_serializable(client):
    response = _post(client, "running.cfg", b"hostname R1\n")
    assert response.status_code == 201
    json.dumps(response.json())
