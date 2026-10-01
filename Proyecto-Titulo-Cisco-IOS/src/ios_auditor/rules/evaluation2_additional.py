"""Controles adicionales explícitos, sin publicar valores de autenticación."""

from dataclasses import dataclass
import re
from typing import ClassVar

from ios_auditor.domain import AnalysisContext, RuleEvaluation, RuleMetadata, RuleStatus
from ios_auditor.rules.evaluation2 import _blocks, _result

PASS, FAIL, NA, NE = (RuleStatus.PASS, RuleStatus.FAIL,
                      RuleStatus.NOT_APPLICABLE, RuleStatus.NOT_EVALUATED)


def _username_status(tokens: tuple[str, ...]) -> RuleStatus:
    if len(tokens) < 4 or re.fullmatch(r'[^\s"\']+', tokens[1]) is None:
        return NE
    tail = tokens[2:]
    if tail[:1] == ("privilege",):
        if len(tail) < 4 or not tail[1].isascii() or not tail[1].isdigit() or not 0 <= int(tail[1]) <= 15:
            return NE
        tail = tail[2:]
    mechanism, payload = tail[0], tail[1:]
    if mechanism not in {"password", "secret"}:
        return NE
    supported_types = {"0", "7"} if mechanism == "password" else {"0", "5", "8", "9"}
    # A single numeric token is ambiguous (type without payload), not a secret.
    supported = (len(payload) == 1 and not payload[0].isdigit()) or (
        len(payload) == 2 and payload[0] in supported_types)
    if not supported:
        return NE
    return FAIL if mechanism == "password" else PASS


@dataclass(frozen=True, slots=True)
class LocalUserPasswordRule:
    metadata: RuleMetadata
    expected_id: ClassVar[str] = "IOS-AUTH-003"

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation:
        users = [block for block in _blocks(context)
                 if block.head.tokens[:1] == ("username",)]
        grouped: dict[str, list[RuleStatus]] = {}
        for block in users:
            tokens = block.head.tokens
            key = tokens[1] if len(tokens) > 1 else ""
            grouped.setdefault(key, []).append(_username_status(tokens) if not block.children else NE)
        # Multiple directives for the SAME identity may change its effective
        # mechanism. Never guess precedence, even if one directive is password.
        states = [items[0] if len(items) == 1 else NE for items in grouped.values()]
        status = FAIL if FAIL in states else NE if NE in states else PASS if states else NA
        messages = {PASS: "Usuarios locales evaluables con mecanismo secret.",
                    FAIL: "Usuario local evaluable protegido con password en vez de secret.",
                    NA: "Sin usuarios locales globales dentro del alcance.",
                    NE: "Sintaxis de usuario local no soportada o identidad ambigua."}
        return _result(self.metadata, context, status, messages[status])


def _line_interval(tokens: tuple[str, ...]) -> tuple[str, int, int] | None:
    if len(tokens) not in {3, 4} or tokens[1] not in {"console", "vty"}:
        return None
    if tokens[1] == "console" and len(tokens) != 3:
        return None
    if not all(item.isascii() and item.isdigit() for item in tokens[2:]):
        return None
    first, last = int(tokens[2]), int(tokens[-1])
    return (tokens[1], first, last) if first <= last else None


@dataclass(frozen=True, slots=True)
class AdministrativeTimeoutRule:
    metadata: RuleMetadata
    expected_id: ClassVar[str] = "IOS-ADM-003"

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation:
        lines = [block for block in _blocks(context)
                 if block.head.tokens[:2] in {("line", "vty"), ("line", "console")}]
        intervals = [_line_interval(block.head.tokens) for block in lines]
        ambiguous = any(item is None for item in intervals)
        valid = [item for item in intervals if item is not None]
        ambiguous |= any(a[0] == b[0] and max(a[1], b[1]) <= min(a[2], b[2])
                         for index, a in enumerate(valid) for b in valid[index + 1:])
        states = []
        for block in lines:
            directives = [line.tokens for line in block.children
                          if line.tokens[:1] == ("exec-timeout",)
                          or line.tokens[:2] in {("no", "exec-timeout"), ("default", "exec-timeout")}]
            if len(directives) != 1:
                states.append(NE)
                continue
            tokens = directives[0]
            if (tokens[0] != "exec-timeout" or len(tokens) not in {2, 3}
                    or not all(item.isascii() and item.isdigit() for item in tokens[1:])):
                states.append(NE)
            elif all(int(item) == 0 for item in tokens[1:]):
                states.append(FAIL)
            else:
                states.append(PASS)
        status = NE if ambiguous else FAIL if FAIL in states else NE if NE in states else PASS if states else NA
        messages = {PASS: "Líneas administrativas evaluables con timeout explícito no nulo.",
                    FAIL: "Timeout de sesión administrativa explícitamente deshabilitado.",
                    NA: "Sin líneas VTY o consola dentro del alcance.",
                    NE: "Timeout ausente, sintaxis no soportada o líneas ambiguas."}
        return _result(self.metadata, context, status, messages[status])
