"""Fuera de testpaths normal. Solo ejecutar manualmente con bandera y gateway configurado."""
import os
from pathlib import Path
from uuid import uuid4

import pytest

from ios_auditor.ai.client import OmniRouteClient
from ios_auditor.ai.service import ExplanationService, build_context
from ios_auditor.ai.settings import AISettings
from ios_auditor.services.analyzer import analyze_bytes

pytestmark=pytest.mark.skipif(
    os.getenv('NETAUDIT_RUN_LIVE_AI_TESTS')!='1' or bool(os.getenv('CI')),
    reason='Requiere activación manual explícita y nunca se ejecuta en CI.',
)


def test_live_explanation_of_deterministic_synthetic_findings():
    root=Path(__file__).resolve().parents[1]
    result=analyze_bytes((root/'samples/evaluacion_2/escenario_inseguro.cfg').read_bytes(),source_name='synthetic-live.cfg')
    settings=AISettings.from_env()
    assert settings.enabled and settings.model
    context=build_context(uuid4(),result.findings)
    response=ExplanationService(settings,OmniRouteClient(settings)).explain(context)
    assert response.source=='ai'
    assert {f.rule_id for f in response.explanation.findings}=={f.rule_id for f in context.findings}
