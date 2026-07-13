from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

from ios_auditor.domain import RuleMetadata, Severity


REQUIRED_FIELDS = frozenset(
    {
        "id",
        "version",
        "name",
        "category",
        "description",
        "default_severity",
        "required_sources",
        "applicable_platforms",
        "risk",
        "recommendation",
        "references",
        "false_positives",
        "exceptions",
        "enabled",
    }
)


class MetadataError(ValueError):
    """Metadatos de reglas ausentes, inválidos o inconsistentes."""


def _required_text(data: dict[str, Any], field: str, filename: str) -> str:
    value = data[field]
    if not isinstance(value, str) or not value.strip():
        raise MetadataError(f"{filename}: '{field}' debe ser texto no vacío.")
    return value.strip()


def _string_tuple(data: dict[str, Any], field: str, filename: str) -> tuple[str, ...]:
    value = data[field]
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise MetadataError(f"{filename}: '{field}' debe ser una lista de textos.")
    return tuple(item.strip() for item in value)


def _parse_metadata(data: Any, filename: str) -> RuleMetadata:
    if not isinstance(data, dict):
        raise MetadataError(f"{filename}: el YAML debe contener un mapa.")

    missing = sorted(REQUIRED_FIELDS - data.keys())
    if missing:
        raise MetadataError(
            f"{filename}: faltan campos obligatorios: {', '.join(missing)}."
        )

    severity_value = _required_text(data, "default_severity", filename)
    try:
        severity = Severity(severity_value)
    except ValueError as exc:
        raise MetadataError(
            f"{filename}: severidad inválida '{severity_value}'."
        ) from exc

    enabled = data["enabled"]
    if not isinstance(enabled, bool):
        raise MetadataError(f"{filename}: 'enabled' debe ser booleano.")

    return RuleMetadata(
        id=_required_text(data, "id", filename),
        version=_required_text(data, "version", filename),
        name=_required_text(data, "name", filename),
        category=_required_text(data, "category", filename),
        description=_required_text(data, "description", filename),
        default_severity=severity,
        required_sources=_string_tuple(data, "required_sources", filename),
        applicable_platforms=_string_tuple(data, "applicable_platforms", filename),
        risk=_required_text(data, "risk", filename),
        recommendation=_required_text(data, "recommendation", filename),
        references=_string_tuple(data, "references", filename),
        false_positives=_string_tuple(data, "false_positives", filename),
        exceptions=_string_tuple(data, "exceptions", filename),
        enabled=enabled,
    )


def load_metadata_files(
    directory: Path, expected_filenames: Iterable[str]
) -> tuple[RuleMetadata, ...]:
    root = directory.resolve()
    metadata_by_id: dict[str, RuleMetadata] = {}

    for filename in tuple(expected_filenames):
        if Path(filename).name != filename or Path(filename).suffix not in {".yaml", ".yml"}:
            raise MetadataError(f"Nombre de archivo YAML no permitido: {filename}")

        path = (root / filename).resolve()
        if path.parent != root:
            raise MetadataError(f"Ruta de metadatos fuera del directorio permitido: {filename}")
        if not path.is_file():
            raise MetadataError(f"No existe el archivo de metadatos esperado: {filename}")

        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise MetadataError(f"{filename}: YAML inválido.") from exc
        except OSError as exc:
            raise MetadataError(f"{filename}: no fue posible leer el archivo.") from exc

        metadata = _parse_metadata(data, filename)
        if metadata.id in metadata_by_id:
            raise MetadataError(f"ID de regla duplicado: {metadata.id}")
        metadata_by_id[metadata.id] = metadata

    return tuple(metadata_by_id.values())
