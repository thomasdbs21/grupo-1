from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RuleStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_EVALUATED = "NOT_EVALUATED"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class Evidence:
    source: str
    sha256: str
    line_number: int | None
    content: str


@dataclass(frozen=True, slots=True)
class VtySection:
    header: str
    header_line_number: int
    transport_inputs: tuple[tuple[int, tuple[str, ...]], ...]


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    source_path: str
    sha256: str
    original_content: str
    normalized_lines: tuple[str, ...]
    vty_sections: tuple[VtySection, ...]


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    rule_id: str
    rule_name: str
    status: RuleStatus
    severity: Severity
    message: str
    recommendation: str
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str
    rule_name: str
    severity: Severity
    message: str
    recommendation: str
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    source_path: str
    sha256: str
    evaluations: tuple[RuleEvaluation, ...]
    findings: tuple[Finding, ...]
