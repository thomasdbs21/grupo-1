"""Recoleccion SSH de solo lectura para dispositivos Cisco IOS e IOS XE."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID, uuid4

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)


ALLOWED_COMMANDS = frozenset(
    {
        "show running-config",
        "show version",
        "show ip interface brief",
        "show ip ssh",
    }
)


class NetmikoConnection(Protocol):
    """Operaciones minimas utilizadas de una conexion Netmiko."""

    def send_command(self, command_string: str) -> str: ...

    def disconnect(self) -> None: ...


ConnectionFactory = Callable[..., NetmikoConnection]


class CollectorError(Exception):
    """Error base seguro del recolector SSH."""


class CommandNotAllowedError(CollectorError):
    """El comando solicitado no pertenece a la lista blanca exacta."""


class CollectorAuthenticationError(CollectorError):
    """La autenticacion SSH fue rechazada."""


class CollectorTimeoutError(CollectorError):
    """La conexion SSH excedio el tiempo disponible."""


class CollectorConnectionError(CollectorError):
    """Ocurrio otro error seguro durante la sesion SSH."""


@dataclass(frozen=True, slots=True)
class CommandEvidence:
    """Evidencia inmutable obtenida al ejecutar un comando autorizado."""

    execution_id: UUID
    device_host: str
    command: str
    collected_at: datetime
    raw_output: str = field(repr=False)
    normalized_output: str = field(repr=False)
    sha256: str


@dataclass(slots=True)
class NetmikoCollector:
    """Ejecuta exclusivamente comandos show autorizados en una sesion SSH."""

    host: str
    port: int
    username: str = field(repr=False)
    password: str = field(repr=False)
    connection_factory: ConnectionFactory = field(
        default=ConnectHandler,
        repr=False,
    )

    def collect(
        self,
        commands: str | Iterable[str],
        *,
        execution_id: UUID | None = None,
    ) -> tuple[CommandEvidence, ...]:
        """Recopila uno o varios comandos validados usando una sola conexion."""

        normalized_commands = self._validate_commands(commands)
        run_id = execution_id or uuid4()
        connection: NetmikoConnection | None = None
        operation_failed = True

        try:
            connection = self.connection_factory(
                device_type="cisco_ios",
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
            )
            evidence = tuple(
                self._collect_command(connection, command, run_id)
                for command in normalized_commands
            )
            operation_failed = False
            return evidence
        except NetmikoAuthenticationException:
            raise CollectorAuthenticationError(
                "No fue posible autenticar el dispositivo por SSH."
            ) from None
        except NetmikoTimeoutException:
            raise CollectorTimeoutError(
                "La conexion SSH con el dispositivo excedio el tiempo permitido."
            ) from None
        except CollectorError:
            raise
        except Exception as error:
            raise CollectorConnectionError(
                f"Fallo inesperado durante la sesion SSH ({type(error).__name__})."
            ) from None
        finally:
            if connection is not None:
                try:
                    connection.disconnect()
                except Exception:
                    if not operation_failed:
                        raise CollectorConnectionError(
                            "No fue posible cerrar correctamente la sesion SSH."
                        ) from None

    @staticmethod
    def _validate_commands(commands: str | Iterable[str]) -> tuple[str, ...]:
        candidates = (commands,) if isinstance(commands, str) else tuple(commands)
        if not candidates:
            raise CommandNotAllowedError("Debe indicar al menos un comando autorizado.")

        normalized_commands: list[str] = []
        for command in candidates:
            if not isinstance(command, str):
                raise CommandNotAllowedError("El comando solicitado no esta autorizado.")
            normalized = command.strip().lower()
            if normalized not in ALLOWED_COMMANDS:
                raise CommandNotAllowedError("El comando solicitado no esta autorizado.")
            normalized_commands.append(normalized)
        return tuple(normalized_commands)

    def _collect_command(
        self,
        connection: NetmikoConnection,
        command: str,
        execution_id: UUID,
    ) -> CommandEvidence:
        raw_output = connection.send_command(command)
        if not isinstance(raw_output, str):
            raise CollectorConnectionError(
                "El dispositivo devolvio una salida SSH no textual."
            )
        return CommandEvidence(
            execution_id=execution_id,
            device_host=self.host,
            command=command,
            collected_at=datetime.now(timezone.utc),
            raw_output=raw_output,
            normalized_output=_normalize_line_endings(raw_output),
            sha256=hashlib.sha256(raw_output.encode("utf-8")).hexdigest(),
        )


def _normalize_line_endings(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")
