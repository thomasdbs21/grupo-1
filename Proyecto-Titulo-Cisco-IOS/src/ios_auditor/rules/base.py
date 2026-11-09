from __future__ import annotations

from typing import Protocol

from ios_auditor.domain import AnalysisContext, RuleEvaluation, RuleMetadata


# Contrato común: una regla recibe contexto y devuelve una evaluación.
class Rule(Protocol):
    expected_id: str
    metadata: RuleMetadata

    def evaluate(self, context: AnalysisContext) -> RuleEvaluation: ...
