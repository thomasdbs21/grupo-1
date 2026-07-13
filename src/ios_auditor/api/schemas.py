from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from ios_auditor.domain import RuleStatus, Severity


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorDetail(ApiModel):
    code: str
    message: str


class ErrorResponse(ApiModel):
    error: ErrorDetail


class HealthResponse(ApiModel):
    status: Literal["ok"]
    service: str
    version: str


class RuleSummaryResponse(ApiModel):
    id: str
    version: str
    name: str
    category: str
    default_severity: Severity
    description: str
    required_sources: list[str]


class EvidenceResponse(ApiModel):
    source: str
    sha256: str
    line_number: int | None
    content: str


class RuleEvaluationResponse(ApiModel):
    rule_id: str
    rule_name: str
    status: RuleStatus
    severity: Severity
    message: str
    recommendation: str
    evidence: list[EvidenceResponse]


class FindingResponse(ApiModel):
    rule_id: str
    rule_name: str
    severity: Severity
    message: str
    recommendation: str
    evidence: list[EvidenceResponse]


class AnalysisResponse(ApiModel):
    analysis_id: str
    source_name: str
    sha256: str
    created_at: datetime
    status: Literal["COMPLETED"]
    evaluations: list[RuleEvaluationResponse]
    findings: list[FindingResponse]
    total_evaluations: int
    total_findings: int
    status_summary: dict[str, int]
    finding_severity_summary: dict[str, int]


class AnalysisCreatedResponse(AnalysisResponse):
    pass
