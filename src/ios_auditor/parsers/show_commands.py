"""Parsing determinista de salidas show mediante recursos TextFSM propios."""

from __future__ import annotations

from importlib.resources import files
from types import MappingProxyType
from typing import Callable

import textfsm

from ios_auditor.domain.models import (
    InterfaceBriefEntry,
    InterfaceStatus,
    ProtocolStatus,
    ShowCommandData,
    ShowIpInterfaceBriefData,
    ShowIpSshData,
    ShowVersionData,
)


SUPPORTED_SHOW_COMMANDS = MappingProxyType(
    {
        "show version": "cisco_ios_show_version.textfsm",
        "show ip interface brief": "cisco_ios_show_ip_interface_brief.textfsm",
        "show ip ssh": "cisco_ios_show_ip_ssh.textfsm",
    }
)


class ShowCommandParseError(ValueError):
    """Error base seguro al estructurar una salida show."""


class UnsupportedShowCommandError(ShowCommandParseError):
    """El comando no pertenece al alcance de parsing del incremento."""


class EmptyShowOutputError(ShowCommandParseError):
    """La salida show no contiene texto analizable."""


class TemplateResourceError(ShowCommandParseError):
    """La plantilla requerida no está disponible o no es válida."""


class ShowOutputFormatError(ShowCommandParseError):
    """La salida no coincide con el formato esperado."""


class InvalidStructuredDataError(ShowCommandParseError):
    """TextFSM produjo valores que no cumplen el contrato del dominio."""


def normalize_show_output(value: str) -> str:
    """Normaliza solamente CRLF y CR, conservando el contenido restante."""

    return value.replace("\r\n", "\n").replace("\r", "\n")


def _parse_rows(template_name: str, output: str) -> tuple[dict[str, str], ...]:
    resource = files("ios_auditor.resources.textfsm").joinpath(template_name)
    try:
        with resource.open("r", encoding="utf-8") as template_stream:
            template = textfsm.TextFSM(template_stream)
    except (FileNotFoundError, OSError, textfsm.TextFSMTemplateError):
        raise TemplateResourceError(
            "No fue posible cargar la plantilla TextFSM requerida."
        ) from None

    try:
        parsed_rows = template.ParseText(output)
    except textfsm.TextFSMError:
        raise ShowOutputFormatError(
            "La salida no coincide con el formato esperado."
        ) from None

    try:
        return tuple(
            dict(zip(template.header, row, strict=True)) for row in parsed_rows
        )
    except (TypeError, ValueError) as exc:
        raise InvalidStructuredDataError(
            "La plantilla produjo una estructura incompatible."
        ) from None


def _optional(value: str) -> str | None:
    normalized = value.strip()
    return normalized or None


def _single_row(rows: tuple[dict[str, str], ...]) -> dict[str, str]:
    if len(rows) != 1:
        raise ShowOutputFormatError(
            "La salida no contiene exactamente un registro reconocible."
        )
    return rows[0]


def _build_show_version(rows: tuple[dict[str, str], ...]) -> ShowVersionData:
    row = _single_row(rows)
    version = row.get("IOS_VERSION", "").strip()
    if not version:
        raise InvalidStructuredDataError(
            "La versión del sistema operativo no es válida."
        )
    return ShowVersionData(
        ios_version=version,
        platform=_optional(row.get("PLATFORM", "")),
        software_image=_optional(row.get("SOFTWARE_IMAGE", "")),
        uptime=_optional(row.get("UPTIME", "")),
    )


def _build_interfaces(
    rows: tuple[dict[str, str], ...],
) -> ShowIpInterfaceBriefData:
    if not rows:
        raise ShowOutputFormatError(
            "La salida no contiene interfaces reconocibles."
        )

    interfaces: list[InterfaceBriefEntry] = []
    try:
        for row in rows:
            name = row.get("INTERFACE", "").strip()
            if not name:
                raise ValueError
            address = row.get("IP_ADDRESS", "").strip()
            interfaces.append(
                InterfaceBriefEntry(
                    name=name,
                    ip_address=None if address.lower() == "unassigned" else address,
                    method=_optional(row.get("METHOD", "")),
                    status=InterfaceStatus(
                        " ".join(row.get("STATUS", "").lower().split())
                    ),
                    protocol=ProtocolStatus(
                        row.get("PROTOCOL", "").strip().lower()
                    ),
                )
            )
    except ValueError:
        raise InvalidStructuredDataError(
            "Una interfaz contiene valores estructurados inválidos."
        ) from None
    return ShowIpInterfaceBriefData(interfaces=tuple(interfaces))


def _optional_int(value: str) -> int | None:
    normalized = value.strip()
    if not normalized:
        return None
    parsed = int(normalized)
    if parsed < 0:
        raise ValueError
    return parsed


def _build_show_ip_ssh(rows: tuple[dict[str, str], ...]) -> ShowIpSshData:
    row = _single_row(rows)
    state = row.get("STATE", "").strip().lower()
    if state not in {"enabled", "disabled"}:
        raise InvalidStructuredDataError("El estado SSH no es válido.")
    try:
        return ShowIpSshData(
            enabled=state == "enabled",
            version=_optional(row.get("VERSION", "")),
            authentication_timeout_seconds=_optional_int(
                row.get("AUTH_TIMEOUT", "")
            ),
            authentication_retries=_optional_int(row.get("AUTH_RETRIES", "")),
        )
    except ValueError:
        raise InvalidStructuredDataError(
            "Los parámetros de autenticación SSH no son válidos."
        ) from None


_BUILDERS: MappingProxyType[
    str, Callable[[tuple[dict[str, str], ...]], ShowCommandData]
] = MappingProxyType(
    {
        "show version": _build_show_version,
        "show ip interface brief": _build_interfaces,
        "show ip ssh": _build_show_ip_ssh,
    }
)


def parse_show_command(command: str, raw_output: str) -> ShowCommandData:
    """Convierte una salida autorizada en un modelo inmutable y tipado."""

    if not isinstance(command, str):
        raise UnsupportedShowCommandError("El comando show no está soportado.")
    normalized_command = command.strip().lower()
    template_name = SUPPORTED_SHOW_COMMANDS.get(normalized_command)
    if template_name is None:
        raise UnsupportedShowCommandError("El comando show no está soportado.")
    if not isinstance(raw_output, str) or not raw_output.strip():
        raise EmptyShowOutputError("La salida del comando show está vacía.")

    normalized_output = normalize_show_output(raw_output)
    rows = _parse_rows(template_name, normalized_output)
    return _BUILDERS[normalized_command](rows)
