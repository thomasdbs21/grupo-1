from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from ios_auditor.domain import RuleMetadata
from ios_auditor.rules.base import Rule
from ios_auditor.rules.increment8 import (
    NtpServerRule,
    RemoteSyslogServerRule,
    SmallServersRule,
    SshVersionRule,
)
from ios_auditor.rules.metadata import MetadataError, load_metadata_files
from ios_auditor.rules.pilot import EnablePasswordRule, HttpServerRule, TelnetVtyRule


OFFICIAL_RULE_FILES = (
    "IOS-ADM-001.yaml",
    "IOS-SRV-001.yaml",
    "IOS-AUTH-001.yaml",
    "IOS-ADM-002.yaml",
    "IOS-SRV-002.yaml",
    "IOS-NTP-001.yaml",
    "IOS-LOG-001.yaml",
)
RULE_TYPES = (
    TelnetVtyRule,
    HttpServerRule,
    EnablePasswordRule,
    SshVersionRule,
    SmallServersRule,
    NtpServerRule,
    RemoteSyslogServerRule,
)


class RegistryError(ValueError):
    """El registro de reglas es inválido o inconsistente."""


class RuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}

    def register(self, rule_type: type, metadata: RuleMetadata) -> None:
        expected_id = getattr(rule_type, "expected_id", None)
        if expected_id != metadata.id:
            raise RegistryError(
                f"El ID YAML '{metadata.id}' no coincide con la regla Python "
                f"'{expected_id}'."
            )
        if metadata.id in self._rules:
            raise RegistryError(f"ID de regla duplicado en el registro: {metadata.id}")
        self._rules[metadata.id] = rule_type(metadata)

    def get(self, rule_id: str) -> Rule:
        try:
            return self._rules[rule_id]
        except KeyError as exc:
            raise RegistryError(f"Regla no registrada: {rule_id}") from exc

    def list_rules(self, *, enabled_only: bool = False) -> tuple[Rule, ...]:
        rules = tuple(self._rules.values())
        if enabled_only:
            return tuple(rule for rule in rules if rule.metadata.enabled)
        return rules


def build_registry(
    metadata_items: Iterable[RuleMetadata],
    rule_types: Iterable[type] = RULE_TYPES,
) -> RuleRegistry:
    metadata_sequence = tuple(metadata_items)
    metadata_by_id = {item.id: item for item in metadata_sequence}
    if len(metadata_by_id) != len(metadata_sequence):
        raise RegistryError("Los metadatos contienen IDs duplicados.")

    registry = RuleRegistry()
    for rule_type in rule_types:
        expected_id = getattr(rule_type, "expected_id", None)
        if expected_id not in metadata_by_id:
            raise RegistryError(f"No hay metadatos para la regla Python '{expected_id}'.")
        registry.register(rule_type, metadata_by_id.pop(expected_id))

    if metadata_by_id:
        raise RegistryError(
            "Hay metadatos sin regla Python asociada: "
            + ", ".join(sorted(metadata_by_id))
        )
    return registry


def load_registry_from_directory(
    directory: Path, expected_filenames: Iterable[str] = OFFICIAL_RULE_FILES
) -> RuleRegistry:
    metadata = load_metadata_files(directory, expected_filenames)
    return build_registry(metadata)


@lru_cache(maxsize=1)
def get_default_registry() -> RuleRegistry:
    resource_directory = files("ios_auditor.resources.rules")
    try:
        directory = Path(str(resource_directory))
        return load_registry_from_directory(directory)
    except (MetadataError, RegistryError) as exc:
        raise RegistryError(f"No fue posible construir el registro oficial: {exc}") from exc
