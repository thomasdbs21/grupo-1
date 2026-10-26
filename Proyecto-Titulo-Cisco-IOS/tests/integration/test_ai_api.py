import json
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from ios_auditor.ai.errors import AIError, AIErrorCode
from ios_auditor.ai.repository import AIContextRepository
from ios_auditor.ai.service import ExplanationService
from ios_auditor.ai.settings import AISettings
from ios_auditor.api.app import app
from ios_auditor.api.dependencies import get_ai_context_repository, get_ai_service, get_analysis_repository, get_connection_factory
from ios_auditor.api.repository import InMemoryAnalysisRepository

ROOT=Path(__file__).resolve().parents[2]


class Provider:
    def __init__(self):self.calls=[];self.error=None
    def reachable(self):return True
    def complete(self,messages):
        self.calls.append(messages)
        if self.error:raise AIError(self.error)
        data=json.loads(messages[1]["content"])["UNTRUSTED_DATA"]
        return json.dumps(dict(summary="Revisar los hallazgos del motor.", findings=[dict(
            rule_id=f["rule_id"], explanation="Explicación basada en el hallazgo.",
            technical_impact="Considerar el funcionamiento de la red.", priority_reason="Severidad recibida del motor.",
            manual_review="Revisar evidencia de solo lectura.") for f in data["findings"]],
            limitations=["Datos sintéticos de prueba."],question_answer="Revisar el hallazgo documentado." if data["question"] else None))


@pytest.fixture
def setup():
    repo=AIContextRepository();analyses=InMemoryAnalysisRepository();provider=Provider()
    service=ExplanationService(AISettings(enabled=True,model="synthetic/free-model"),provider)
    app.dependency_overrides[get_ai_context_repository]=lambda:repo
    app.dependency_overrides[get_analysis_repository]=lambda:analyses
    app.dependency_overrides[get_ai_service]=lambda:service
    with TestClient(app,raise_server_exceptions=False) as client:
        yield client,repo,provider,analyses
    app.dependency_overrides.clear()


def upload(client):
    result=client.post('/api/v1/analyses',files={'file':('synthetic.cfg',(ROOT/'samples/evaluacion_2/escenario_inseguro.cfg').read_bytes())})
    assert result.status_code==201
    return result.json()


def test_offline_analysis_registers_context_and_explanation_uses_backend_findings(setup):
    client,repo,provider,_=setup
    analysis=upload(client);reference=analysis['analysis_id']
    context=repo.get(UUID(reference))
    assert context and context.total_findings==analysis['total_findings']
    response=client.post(f'/api/v1/analyses/{reference}/ai-explanation')
    assert response.status_code==200
    assert {f['rule_id'] for f in response.json()['explanation']['findings']}=={f['rule_id'] for f in analysis['findings']}
    assert client.get(f'/api/v1/analyses/{reference}').json()==analysis
    assert len(provider.calls)==1


@pytest.mark.parametrize('payload',[{'question':'¿Qué revisar primero?'}, {}, None])
def test_question_is_optional_and_valid(setup,payload):
    client,_,provider,_=setup;analysis=upload(client)
    response=client.post(f"/api/v1/analyses/{analysis['analysis_id']}/ai-explanation",json=payload)
    assert response.status_code==200
    if payload and payload.get('question'):assert response.json()['explanation']['question_answer']


@pytest.mark.parametrize('payload',[{'question':''},{'question':'  '},{'question':'x'*501},{'findings':[{'rule_id':'IOS-FAKE-999'}]}])
def test_question_validation_and_user_supplied_findings_are_rejected(setup,payload):
    client,_,provider,_=setup;analysis=upload(client)
    assert client.post(f"/api/v1/analyses/{analysis['analysis_id']}/ai-explanation",json=payload).status_code==422
    assert not provider.calls


def test_unknown_analysis_returns_404_without_llm(setup):
    client,_,provider,_=setup
    assert client.post(f'/api/v1/analyses/{uuid4()}/ai-explanation',json={}).status_code==404
    assert not provider.calls


@pytest.mark.parametrize('code',list(AIErrorCode))
def test_provider_failures_do_not_change_or_hide_deterministic_results(setup,code,caplog):
    client,_,provider,_=setup;analysis=upload(client);provider.error=code
    response=client.post(f"/api/v1/analyses/{analysis['analysis_id']}/ai-explanation")
    assert response.status_code in {502,503,504}
    assert response.json()['error']['code']==code.value
    assert client.get(f"/api/v1/analyses/{analysis['analysis_id']}").json()==analysis
    assert 'SYNTHETIC' not in caplog.text


def test_empty_backend_findings_do_not_call_provider(setup):
    client,repo,provider,_=setup
    from ios_auditor.ai.service import build_context
    reference=uuid4();repo.put(build_context(reference,()))
    response=client.post(f'/api/v1/analyses/{reference}/ai-explanation')
    assert response.status_code==200 and response.json()['source']=='deterministic'
    assert provider.calls==[]


def test_ai_health_exposes_only_safe_booleans(setup):
    client,_,provider,_=setup
    assert client.get('/api/v1/ai/health').json()=={'enabled':True,'gateway_reachable':True,'model_configured':True}
    assert not provider.calls


def test_device_execution_id_registers_only_sanitized_context(setup):
    client,repo,provider,_=setup
    outputs={
        'show running-config':'line vty 0 4\n transport input ssh\nip http secure-server\n',
        'show version':'Cisco IOS XE Software, Version 16.09.05\n',
        'show ip interface brief':'Interface IP-Address OK? Method Status Protocol\nGigabitEthernet1 unassigned YES unset up down\n',
        'show ip ssh':'SSH Enabled - version 2.0\nAuthentication timeout: 120 secs; Authentication retries: 3\n',
        'show interfaces':'GigabitEthernet1 is down, line protocol is down\n',
        'show access-lists':'',
        'show ntp associations':'address ref clock st when poll reach delay offset disp\n',
        'show ip ospf neighbor':'Neighbor ID Pri State Dead Time Address Interface\n',
    }
    connection=MagicMock();connection.send_command.side_effect=lambda cmd:outputs[cmd]
    factory=MagicMock(return_value=connection)
    app.dependency_overrides[get_connection_factory]=lambda:factory
    response=client.post('/api/v1/device-analyses',json=dict(host='192.168.50.10',port=22,username='synthetic-user',password='SYNTHETIC_PASSWORD_NOT_REAL'))
    assert response.status_code==200
    data=response.json();reference=data['execution_id'];context=repo.get(UUID(reference))
    assert context and context.total_findings==data['total_findings']
    serialized=context.model_dump_json()
    assert all(value not in serialized for value in ['192.168.50.10','synthetic-user','SYNTHETIC_PASSWORD_NOT_REAL'])
    assert connection.send_command.call_count==8
    explained=client.post(f'/api/v1/analyses/{reference}/ai-explanation')
    assert explained.status_code==200 and len(provider.calls)==1
    assert data['total_evaluations']==21


def test_failure_registering_optional_context_does_not_break_analysis(setup,monkeypatch,caplog):
    client,repo,_,_=setup
    def fail(_):raise RuntimeError('SYNTHETIC_VALUE_NOT_TO_EXPOSE')
    monkeypatch.setattr(repo,'put',fail)
    assert upload(client)['total_evaluations']==14
    assert 'ai_context_registration_failed' in caplog.text
    assert 'SYNTHETIC_VALUE_NOT_TO_EXPOSE' not in caplog.text
