"""Redacción determinista previa a cualquier límite o serialización del prompt."""
from __future__ import annotations

import ipaddress
import re
import unicodedata

REDACTED = "<REDACTED>"
MAX_EVIDENCE_CHARACTERS = 500
MAX_EVIDENCE_PER_FINDING = 2
MAX_FINDINGS = 32
MAX_CONTEXT_BYTES = 24000
MAX_INPUT_TEXT = 65536

_PRIVATE = re.compile(
    r"-----BEGIN [A-Z0-9 ]*(?:PRIVATE KEY|CERTIFICATE)-----.*?"
    r"(?:-----END [A-Z0-9 ]+-----|\Z)", re.I | re.S,
)
_CISCO_LINES = [
    (r"\benable\s+(secret|password)\b[^\r\n]*", r"enable \1 <REDACTED>"),
    (r"\busername\s+\S+[^\r\n]*?\b(secret|password)\b[^\r\n]*", r"username <REDACTED> \1 <REDACTED>"),
    (r"\bsnmp-server\s+community\b[^\r\n]*", "snmp-server community <REDACTED>"),
    (r"\bsnmp-server\s+user\b[^\r\n]*", "snmp-server user <REDACTED>"),
    (r"\b(?:radius-server|tacacs-server)\s+key\b[^\r\n]*", "server key <REDACTED>"),
    (r"\bkey-string\b[^\r\n]*", "key-string <REDACTED>"),
    (r"\bneighbor\s+\S+\s+password\b[^\r\n]*", "neighbor <REDACTED> password <REDACTED>"),
    (r"\bcrypto\s+isakmp\s+key\b[^\r\n]*", "crypto isakmp key <REDACTED>"),
    (r"\b(?:ntp\s+)?authentication-key\b[^\r\n]*", "authentication-key <REDACTED>"),
    (r"\bmessage-digest-key\b[^\r\n]*", "message-digest-key <REDACTED>"),
    (r"\bkey\s+7\s+\S+", "key 7 <REDACTED>"),
    (r"\bhostname\s+\S+", "hostname <REDACTED>"),
]
_ASSIGNMENT = re.compile(
    r"\b(api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|passwd|secret|client_secret)"
    r"[\"']?\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\s,;}]+)", re.I,
)
_TOKENS = re.compile(r"\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9]{12,}|github_pat_[A-Za-z0-9_]{12,})\b")
_IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
_IPV6 = re.compile(r"(?<![\w])(?:[a-fA-F0-9]{0,4}:){2,}[a-fA-F0-9:]+(?:%[\w]+)?")


def _redact_ip(match: re.Match) -> str:
    try:
        ipaddress.ip_address(match.group())
        return REDACTED
    except ValueError:
        return match.group()


def sanitize_text(value: str) -> str:
    """No reconstruye una configuración; elimina secretos y localizadores reconocibles."""
    # Una entrada demasiado extensa se omite completa: nunca cortar un secreto antes de detectarlo.
    if len(value) > MAX_INPUT_TEXT:
        return "<REDACTED: fragmento excede el límite de entrada>"
    value = unicodedata.normalize("NFKC", value)
    value = "".join(c for c in value if c in "\n\r\t" or unicodedata.category(c) != "Cc")
    value = _PRIVATE.sub(REDACTED, value)
    for pattern, replacement in _CISCO_LINES:
        value = re.sub(pattern, replacement, value, flags=re.I)
    value = re.sub(r"\bssh-(?:rsa|ed25519)\s+\S+(?:[^\r\n]*)", REDACTED, value, flags=re.I)
    value = re.sub(r"\bBearer\s+[^\s,;]+", "Bearer <REDACTED>", value, flags=re.I)
    value = _ASSIGNMENT.sub(lambda m: m.group(1) + "=<REDACTED>", value)
    value = _TOKENS.sub(REDACTED, value)
    value = _IPV4.sub(_redact_ip, value)
    value = _IPV6.sub(_redact_ip, value)
    value = re.sub(r"\b(?:serial(?: number)?|processor board id)\s*[:=]?\s*\S+", "serial <REDACTED>", value, flags=re.I)
    return value.strip()


def bounded_text(value: str, limit: int) -> str:
    return sanitize_text(value)[:limit]
