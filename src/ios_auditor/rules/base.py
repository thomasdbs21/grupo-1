from __future__ import annotations

from typing import Protocol

from ios_auditor.domain import AnalysisContext, RuleEvaluation


class Rule(Protocol):
    rule_id: str
    name: str

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation: ...
