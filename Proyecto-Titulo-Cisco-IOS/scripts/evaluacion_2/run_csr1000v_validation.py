"""Validación manual de solo lectura; importar este módulo nunca abre SSH."""

from __future__ import annotations

from dataclasses import dataclass, field
import getpass
from pathlib import Path
import re
import sys
import warnings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ios_auditor.collectors import netmiko_collector
from ios_auditor.domain import FullDeviceAnalysisResult
from ios_auditor.services import CANONICAL_EVIDENCE_COMMANDS, collect_and_analyze_device


@dataclass
class SessionAudit:
    attempts: int = 0
    sessions: int = 0
    disconnects: int = 0
    commands: list[str] = field(default_factory=list)


class ReadOnlyConnection:
    """Audita exclusivamente las operaciones públicas usadas por el collector."""

    def __init__(self, connection, audit: SessionAudit) -> None:
        self._connection = connection
        self._audit = audit

    def send_command(self, command_string: str) -> str:
        index = len(self._audit.commands)
        if (index >= len(CANONICAL_EVIDENCE_COMMANDS)
                or command_string != CANONICAL_EVIDENCE_COMMANDS[index]):
            raise ValueError("Secuencia de consulta no autorizada.")
        self._audit.commands.append(command_string)
        return self._connection.send_command(command_string)

    def disconnect(self) -> None:
        self._connection.disconnect()
        self._audit.disconnects += 1


def audited_factory(audit: SessionAudit):
    def connect(**kwargs):
        if audit.attempts:
            raise ValueError("No se autoriza un segundo intento SSH.")
        audit.attempts += 1
        connection = netmiko_collector.ConnectHandler(**kwargs)
        audit.sessions += 1
        return ReadOnlyConnection(connection, audit)
    return connect


def hidden_input(prompt: str) -> str:
    # Si el terminal no permite ocultar, se aborta antes de leer en modo visible.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        return getpass.getpass(prompt)


def request_connection() -> tuple[str, int, str, str]:
    host = hidden_input("Host (entrada oculta): ").strip()
    port_text = hidden_input("Puerto (Enter = 22, entrada oculta): ").strip()
    port = int(port_text or "22")
    username = hidden_input("Usuario (entrada oculta): ").strip()
    password = hidden_input("Contraseña (entrada oculta): ")
    if not host or not username or not password or not 1 <= port <= 65535:
        raise ValueError("Datos de conexión incompletos o inválidos.")
    return host, port, username, password


def render_result(result: FullDeviceAnalysisResult, audit: SessionAudit) -> str:
    if (audit.sessions != 1 or audit.disconnects != 1
            or tuple(audit.commands) != CANONICAL_EVIDENCE_COMMANDS):
        raise ValueError("La sesión no cumple el contrato de validación.")
    version_evidence = next(item for item in result.evidences if item.command == "show version")
    platform = ("Cisco IOS XE" if re.search(r"Cisco IOS XE", version_evidence.raw_output, re.I)
                else "Cisco IOS/IOS XE (variante no confirmada)")
    lines = ["=" * 60, "VALIDACIÓN REAL - CSR1000V", "=" * 60, "",
             f"Plataforma: {platform}", "Modo: SSH SOLO LECTURA",
             "Sesiones SSH: 1", "Desconexiones: 1",
             f"Comandos canónicos: {len(audit.commands)}/{len(CANONICAL_EVIDENCE_COMMANDS)}", "",
             f"Evidencias recopiladas: {len(result.evidences)}",
             f"Evaluaciones ejecutadas: {len(result.evaluations)}",
             f"Findings: {len(result.findings)}", "",
             f"{'Regla':<16}{'Estado':<20}Severidad"]
    lines.extend(f"{item.rule_id:<16}{item.status.value:<20}{item.severity.value}"
                 for item in result.evaluations)
    lines.extend(("", "Severidad: catálogo técnico de cada regla.",
                  "Solo FAIL genera findings.", "=" * 60))
    return "\n".join(lines)


def main() -> int:
    audit = SessionAudit()
    try:
        host, port, username, password = request_connection()
        result = collect_and_analyze_device(
            host=host, port=port, username=username, password=password,
            connection_factory=audited_factory(audit),
        )
        print(render_result(result, audit))
        return 0
    except (KeyboardInterrupt, EOFError):
        print("Validación cancelada. No se reintentará SSH.")
        return 1
    except Exception:
        # Frontera de consola: nunca imprime excepciones que puedan contener
        # datos de conexión, salidas del dispositivo o errores internos.
        print("ERROR: no fue posible completar la validación real.")
        print(f"Sesiones SSH creadas: {audit.sessions}")
        print(f"Desconexiones confirmadas: {audit.disconnects}")
        print(f"Comandos de consulta intentados: {len(audit.commands)}")
        print("No se reintentará SSH. Revisar acceso, terminal y permisos de lectura.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
