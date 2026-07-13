from __future__ import annotations

from ios_auditor.api.repository import InMemoryAnalysisRepository
from ios_auditor.rules import RuleRegistry, get_default_registry


_repository = InMemoryAnalysisRepository(max_items=100)


def get_analysis_repository() -> InMemoryAnalysisRepository:
    return _repository


def get_rule_registry() -> RuleRegistry:
    return get_default_registry()
