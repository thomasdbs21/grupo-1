from __future__ import annotations

from netmiko import ConnectHandler

from ios_auditor.ai.client import OmniRouteClient
from ios_auditor.ai.repository import AIContextRepository
from ios_auditor.ai.service import ExplanationService
from ios_auditor.ai.settings import AISettings

from ios_auditor.api.repository import InMemoryAnalysisRepository
from ios_auditor.collectors.netmiko_collector import ConnectionFactory
from ios_auditor.rules import RuleRegistry, get_default_registry


_repository = InMemoryAnalysisRepository(max_items=100)


def get_analysis_repository() -> InMemoryAnalysisRepository:
    return _repository


def get_rule_registry() -> RuleRegistry:
    return get_default_registry()


def get_connection_factory() -> ConnectionFactory:
    """Entrega la fábrica real, reemplazable mediante dependency_overrides."""

    return ConnectHandler


# Contexto explicativo separado del repositorio determinista; no conserva entradas crudas.

_ai_context_repository = AIContextRepository(max_items=100)


def get_ai_context_repository() -> AIContextRepository:
    return _ai_context_repository


def get_ai_service() -> ExplanationService:
    settings = AISettings.from_env()
    return ExplanationService(settings, OmniRouteClient(settings))
