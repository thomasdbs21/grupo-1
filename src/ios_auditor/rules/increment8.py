from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
import re
from typing import ClassVar, Callable

from ios_auditor.domain import (
    AnalysisContext,
    Evidence,
    RuleEvaluation,
    RuleMetadata,
    RuleStatus,
)


_SSH_VERSION_1 = ("ip", "ssh", "version", "1")
_SSH_VERSION_2 = ("ip", "ssh", "version", "2")
_SMALL_SERVER_COMMANDS = (
    ("service", "tcp-small-servers"),
    ("service", "udp-small-servers"),
)
_NTP_OPTION_KEYWORDS = frozenset(
    {
        "ip",
        "ipv6",
        "key",
        "maxpoll",
        "minpoll",
        "periodic",
        "prefer",
        "source",
        "version",
        "vrf",
    }
)
_LOCAL_LOGGING_KEYWORDS = frozenset(
    {
        "buffered",
        "console",
        "count",
        "discriminator",
        "esm",
        "facility",
        "filter",
        "history",
        "monitor",
        "on",
        "origin-id",
        "persistent",
        "queue-limit",
        "rate-limit",
        "source-interface",
        "synchronous",
        "trap",
    }
)
_HOSTNAME_RE = re.compile(
    r"(?=.{1,253}\Z)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*\Z"
)


def _tokens(line: str) -> tuple[str, ...]:
    return tuple(line.split())


def _matching_lines(
    context: AnalysisContext, predicate: Callable[[tuple[str, ...]], bool]
) -> tuple[tuple[int, str], ...]:
    return tuple(
        (line_number, line.strip())
        for line_number, line in enumerate(context.original_content.splitlines(), start=1)
        if line.strip() and predicate(_tokens(line.strip()))
    )


def _evidence(
    context: AnalysisContext, content: str, line_number: int | None = None
) -> Evidence:
    return Evidence(
        source=context.source_path,
        sha256=context.sha256,
        line_number=line_number,
        content=content,
    )


def _evaluation(
    metadata: RuleMetadata,
    *,
    status: RuleStatus,
    message: str,
    evidence: tuple[Evidence, ...] = (),
) -> RuleEvaluation:
    return RuleEvaluation(
        rule_id=metadata.id,
        rule_name=metadata.name,
        status=status,
        severity=metadata.default_severity,
        message=message,
        recommendation=metadata.recommendation,
        evidence=evidence,
    )


@dataclass(frozen=True, slots=True)
class SshVersionRule:
    metadata: RuleMetadata
    expected_id: ClassVar[str] = "IOS-ADM-002"

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation:
        version_1_lines = _matching_lines(context, lambda tokens: tokens == _SSH_VERSION_1)
        if version_1_lines:
            return _evaluation(
                self.metadata,
                status=RuleStatus.FAIL,
                message="SSH versión 1 está habilitada explícitamente.",
                evidence=tuple(
                    _evidence(context, "ip ssh version 1", line_number)
                    for line_number, _ in version_1_lines
                ),
            )

        version_2_exists = bool(
            _matching_lines(context, lambda tokens: tokens == _SSH_VERSION_2)
        )
        if version_2_exists:
            return _evaluation(
                self.metadata,
                status=RuleStatus.PASS,
                message="SSH versión 2 está configurada explícitamente.",
                evidence=(_evidence(context, "SSH versión 2: configurada"),),
            )

        return _evaluation(
            self.metadata,
            status=RuleStatus.NOT_EVALUATED,
            message="No existe una directiva explícita de versión SSH.",
        )


@dataclass(frozen=True, slots=True)
class SmallServersRule:
    metadata: RuleMetadata
    expected_id: ClassVar[str] = "IOS-SRV-002"

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation:
        unsafe_lines = _matching_lines(
            context,
            lambda tokens: any(
                tokens[: len(command)] == command for command in _SMALL_SERVER_COMMANDS
            ),
        )
        if unsafe_lines:
            return _evaluation(
                self.metadata,
                status=RuleStatus.FAIL,
                message="Uno o más servicios TCP/UDP pequeños están habilitados.",
                evidence=tuple(
                    _evidence(context, content, line_number)
                    for line_number, content in unsafe_lines
                ),
            )
        return _evaluation(
            self.metadata,
            status=RuleStatus.PASS,
            message="Los servicios TCP/UDP pequeños no están habilitados.",
        )


def _is_valid_ntp_server(tokens: tuple[str, ...]) -> bool:
    if tokens[:2] != ("ntp", "server"):
        return False
    arguments = tokens[2:]
    if not arguments:
        return False
    if arguments[0] == "vrf":
        return len(arguments) >= 3 and arguments[2] not in _NTP_OPTION_KEYWORDS
    if arguments[0] in {"ip", "ipv6"}:
        return len(arguments) >= 2 and arguments[1] not in _NTP_OPTION_KEYWORDS
    return arguments[0] not in _NTP_OPTION_KEYWORDS


@dataclass(frozen=True, slots=True)
class NtpServerRule:
    metadata: RuleMetadata
    expected_id: ClassVar[str] = "IOS-NTP-001"

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation:
        if _matching_lines(context, _is_valid_ntp_server):
            return _evaluation(
                self.metadata,
                status=RuleStatus.PASS,
                message="Existe al menos un servidor NTP configurado.",
                evidence=(_evidence(context, "servidor NTP: configurado"),),
            )
        return _evaluation(
            self.metadata,
            status=RuleStatus.FAIL,
            message="No existe un servidor NTP configurado.",
            evidence=(_evidence(context, "servidor NTP: no configurado"),),
        )


def _is_destination(value: str) -> bool:
    try:
        ip_address(value)
    except ValueError:
        return _HOSTNAME_RE.fullmatch(value) is not None
    return True


def _is_unambiguous_legacy_destination(value: str) -> bool:
    try:
        ip_address(value)
    except ValueError:
        return "." in value and _HOSTNAME_RE.fullmatch(value) is not None
    return True


def _consume_pair(tokens: tuple[str, ...], index: int) -> int | None:
    return index + 2 if index + 1 < len(tokens) else None


def _modern_logging_destination(tokens: tuple[str, ...]) -> bool | None:
    if tokens[:2] != ("logging", "host"):
        return None
    if len(tokens) < 3:
        return False

    index = 2
    if tokens[index] == "ipv6":
        index += 1
        if index >= len(tokens):
            return False
    if not _is_destination(tokens[index]):
        return False
    index += 1

    while index < len(tokens):
        keyword = tokens[index]
        if keyword in {"vrf", "discriminator", "session-id"}:
            next_index = _consume_pair(tokens, index)
        elif keyword == "transport":
            next_index = _consume_pair(tokens, index)
            if next_index is None or tokens[index + 1] not in {"beep", "tcp", "udp"}:
                return False
        elif keyword == "port":
            next_index = _consume_pair(tokens, index)
            if next_index is None or not tokens[index + 1].isdigit():
                return False
        elif keyword in {"xml", "filtered", "sequence-num-session"}:
            next_index = index + 1
        elif keyword == "stream":
            next_index = _consume_pair(tokens, index)
        else:
            return False
        if next_index is None:
            return False
        index = next_index
    return True


def _classify_logging_line(tokens: tuple[str, ...]) -> str:
    modern = _modern_logging_destination(tokens)
    if modern is not None:
        return "destination" if modern else "ambiguous"
    if not tokens or tokens[0] != "logging":
        return "irrelevant"
    if len(tokens) == 1:
        return "local"
    if tokens[1] in _LOCAL_LOGGING_KEYWORDS:
        return "local"
    if len(tokens) == 2 and _is_unambiguous_legacy_destination(tokens[1]):
        return "destination"
    return "ambiguous"


@dataclass(frozen=True, slots=True)
class RemoteSyslogServerRule:
    metadata: RuleMetadata
    expected_id: ClassVar[str] = "IOS-LOG-001"

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation:
        classifications = tuple(
            _classify_logging_line(_tokens(line))
            for line in context.normalized_lines
            if _tokens(line)[:1] == ("logging",)
        )
        if "destination" in classifications:
            return _evaluation(
                self.metadata,
                status=RuleStatus.PASS,
                message="Existe al menos un servidor Syslog remoto configurado.",
                evidence=(
                    _evidence(context, "servidor Syslog remoto: configurado"),
                ),
            )
        if "ambiguous" in classifications:
            return _evaluation(
                self.metadata,
                status=RuleStatus.NOT_EVALUATED,
                message="Existe una directiva Syslog potencialmente remota no reconocida.",
            )
        return _evaluation(
            self.metadata,
            status=RuleStatus.FAIL,
            message="No existe un servidor Syslog remoto configurado.",
            evidence=(
                _evidence(context, "servidor Syslog remoto: no configurado"),
            ),
        )


__all__ = [
    "NtpServerRule",
    "RemoteSyslogServerRule",
    "SmallServersRule",
    "SshVersionRule",
]
