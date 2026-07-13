from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
import yaml

from ios_auditor.rules import get_default_registry
from ios_auditor.rules.metadata import load_metadata_files
from ios_auditor.rules.pilot import TelnetVtyRule
from ios_auditor.rules.registry import (
    OFFICIAL_RULE_FILES,
    RegistryError,
    RuleRegistry,
    load_registry_from_directory,
)
from ios_auditor.services.analyzer import analyze_file


def _official_resource_directory() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "src"
        / "ios_auditor"
        / "resources"
        / "rules"
    )


def _temporary_registry(tmp_path: Path, *, disabled_id: str | None = None):
    source_directory = _official_resource_directory()
    for filename in OFFICIAL_RULE_FILES:
        data = yaml.safe_load((source_directory / filename).read_text(encoding="utf-8"))
        if data["id"] == disabled_id:
            data["enabled"] = False
        (tmp_path / filename).write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    return load_registry_from_directory(tmp_path)


def test_registry_registers_and_gets_rule_by_id():
    registry = get_default_registry()

    rule = registry.get("IOS-ADM-001")

    assert rule.metadata.id == "IOS-ADM-001"
    assert isinstance(rule, TelnetVtyRule)


def test_registry_has_deterministic_order():
    ids = tuple(rule.metadata.id for rule in get_default_registry().list_rules())
    assert ids == ("IOS-ADM-001", "IOS-SRV-001", "IOS-AUTH-001")


def test_registry_rejects_yaml_id_mismatch_with_python_rule(tmp_path):
    source = _official_resource_directory() / "IOS-ADM-001.yaml"
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    data["id"] = "IOS-OTRO-001"
    (tmp_path / "IOS-ADM-001.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    metadata = load_metadata_files(tmp_path, ("IOS-ADM-001.yaml",))[0]
    registry = RuleRegistry()

    with pytest.raises(RegistryError, match="no coincide"):
        registry.register(TelnetVtyRule, metadata)


def test_registry_rejects_duplicate_id():
    metadata = get_default_registry().get("IOS-ADM-001").metadata
    registry = RuleRegistry()
    registry.register(TelnetVtyRule, metadata)

    with pytest.raises(RegistryError, match="duplicado"):
        registry.register(TelnetVtyRule, metadata)


def test_rule_cannot_replace_immutable_metadata():
    rule = get_default_registry().get("IOS-ADM-001")

    with pytest.raises(FrozenInstanceError):
        rule.metadata = replace(rule.metadata, enabled=False)


def test_disabled_rule_is_not_listed_as_enabled(tmp_path):
    registry = _temporary_registry(tmp_path, disabled_id="IOS-SRV-001")

    enabled_ids = tuple(rule.metadata.id for rule in registry.list_rules(enabled_only=True))

    assert "IOS-SRV-001" not in enabled_ids
    assert len(enabled_ids) == 2


def test_disabled_rule_produces_no_evaluation_or_finding(tmp_path):
    metadata_directory = tmp_path / "metadata"
    metadata_directory.mkdir()
    registry = _temporary_registry(
        metadata_directory, disabled_id="IOS-SRV-001"
    )
    path = tmp_path / "running.cfg"
    path.write_text(
        "enable password <FAKE>\nip http server\n"
        "line vty 0 4\n transport input telnet\n",
        encoding="utf-8",
    )

    result = analyze_file(path, registry=registry)
    evaluated_ids = {evaluation.rule_id for evaluation in result.evaluations}
    finding_ids = {finding.rule_id for finding in result.findings}

    assert "IOS-SRV-001" not in evaluated_ids
    assert "IOS-SRV-001" not in finding_ids
    assert len(result.evaluations) == 2
    assert len(result.findings) == 2
