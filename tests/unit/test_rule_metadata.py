from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
import yaml

from ios_auditor.domain import RuleMetadata, Severity
from ios_auditor.rules.metadata import MetadataError, load_metadata_files


def _valid_data(rule_id: str = "IOS-TEST-001") -> dict:
    return {
        "id": rule_id,
        "version": "1.0.0",
        "name": "Regla de prueba",
        "category": "pruebas",
        "description": "Metadatos temporales para pruebas.",
        "default_severity": "MEDIUM",
        "required_sources": ["running-config"],
        "applicable_platforms": ["Cisco IOS"],
        "risk": "Riesgo de prueba.",
        "recommendation": "Recomendación de prueba.",
        "references": ["Referencia de prueba"],
        "false_positives": [],
        "exceptions": [],
        "enabled": True,
    }


def _write_yaml(directory: Path, filename: str, data: dict) -> None:
    (directory / filename).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def test_loads_seven_official_running_config_yaml_files():
    resource_dir = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "ios_auditor"
        / "resources"
        / "rules"
    )
    filenames = (
        "IOS-ADM-001.yaml",
        "IOS-SRV-001.yaml",
        "IOS-AUTH-001.yaml",
        "IOS-ADM-002.yaml",
        "IOS-SRV-002.yaml",
        "IOS-NTP-001.yaml",
        "IOS-LOG-001.yaml",
    )

    metadata = load_metadata_files(resource_dir, filenames)

    assert len(metadata) == 7
    assert {item.id for item in metadata} == {
        "IOS-ADM-001",
        "IOS-AUTH-001",
        "IOS-SRV-001",
        "IOS-ADM-002",
        "IOS-SRV-002",
        "IOS-NTP-001",
        "IOS-LOG-001",
    }
    assert all(item.default_severity in Severity for item in metadata)


def test_increment8_metadata_matches_approved_catalog_contracts():
    resource_dir = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "ios_auditor"
        / "resources"
        / "rules"
    )
    filenames = (
        "IOS-ADM-002.yaml",
        "IOS-SRV-002.yaml",
        "IOS-NTP-001.yaml",
        "IOS-LOG-001.yaml",
    )

    metadata = {
        item.id: item for item in load_metadata_files(resource_dir, filenames)
    }

    assert {
        rule_id: (
            item.name,
            item.category,
            item.default_severity,
            item.required_sources,
        )
        for rule_id, item in metadata.items()
    } == {
        "IOS-ADM-002": (
            "SSH versión 1 habilitada",
            "administración remota",
            Severity.HIGH,
            ("running-config",),
        ),
        "IOS-SRV-002": (
            "Servicios TCP/UDP pequeños habilitados",
            "servicios innecesarios",
            Severity.MEDIUM,
            ("running-config",),
        ),
        "IOS-NTP-001": (
            "Servidor NTP no configurado",
            "NTP",
            Severity.MEDIUM,
            ("running-config",),
        ),
        "IOS-LOG-001": (
            "Servidor Syslog no configurado",
            "Syslog",
            Severity.MEDIUM,
            ("running-config",),
        ),
    }
    assert all(item.description for item in metadata.values())
    assert all(item.recommendation for item in metadata.values())
    assert all(item.references for item in metadata.values())


def test_rule_metadata_is_immutable():
    metadata = RuleMetadata(
        id="IOS-TEST-001",
        version="1.0.0",
        name="Prueba",
        category="pruebas",
        description="Prueba",
        default_severity=Severity.INFO,
        required_sources=("running-config",),
        applicable_platforms=("Cisco IOS",),
        risk="Prueba",
        recommendation="Prueba",
        references=(),
        false_positives=(),
        exceptions=(),
        enabled=True,
    )

    with pytest.raises(FrozenInstanceError):
        metadata.enabled = False


def test_rejects_missing_required_field(tmp_path):
    data = _valid_data()
    del data["recommendation"]
    _write_yaml(tmp_path, "rule.yaml", data)

    with pytest.raises(MetadataError, match="faltan campos obligatorios"):
        load_metadata_files(tmp_path, ("rule.yaml",))


def test_rejects_invalid_yaml(tmp_path):
    (tmp_path / "rule.yaml").write_text("id: [sin cerrar", encoding="utf-8")

    with pytest.raises(MetadataError, match="YAML inválido"):
        load_metadata_files(tmp_path, ("rule.yaml",))


def test_rejects_duplicate_ids(tmp_path):
    _write_yaml(tmp_path, "one.yaml", _valid_data())
    _write_yaml(tmp_path, "two.yaml", _valid_data())

    with pytest.raises(MetadataError, match="duplicado"):
        load_metadata_files(tmp_path, ("one.yaml", "two.yaml"))


def test_rejects_empty_version(tmp_path):
    data = _valid_data()
    data["version"] = ""
    _write_yaml(tmp_path, "rule.yaml", data)

    with pytest.raises(MetadataError, match="version"):
        load_metadata_files(tmp_path, ("rule.yaml",))


def test_rejects_invalid_severity(tmp_path):
    data = _valid_data()
    data["default_severity"] = "URGENT"
    _write_yaml(tmp_path, "rule.yaml", data)

    with pytest.raises(MetadataError, match="severidad inválida"):
        load_metadata_files(tmp_path, ("rule.yaml",))
