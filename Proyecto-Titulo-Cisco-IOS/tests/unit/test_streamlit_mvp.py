import ast
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from ios_auditor.ui.backend import BackendClient, BackendError

ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/'apps/streamlit/app.py'


def analysis():
    return dict(analysis_id=str(uuid4()),total_evaluations=14,total_findings=1,
        status_summary={'PASS':13,'FAIL':1},findings=[dict(rule_id='IOS-SRV-001',rule_name='HTTP',severity='HIGH',
        message='HTTP habilitado',recommendation='Revisar el servicio',evidence=[{'content':'ip http server'}])])


def explanation():
    return dict(context_truncated=False,explanation=dict(summary='Explicación sintética de prueba.',findings=[],limitations=[],question_answer='Revisar la evidencia HTTP.'))


def test_ui_initial_screen_and_password_form():
    app=AppTest.from_file(str(APP)).run()
    assert not app.exception and app.title[0].value=='NetAudit'
    app.radio[0].set_value('Analizar dispositivo').run()
    assert not app.exception
    assert [x.label for x in app.text_input]==['Host IPv4 privado','Usuario','Contraseña']
    assert app.text_input[2].proto.type==app.text_input[2].proto.PASSWORD


def test_ui_keeps_findings_visible_when_ai_fails(monkeypatch):
    data=analysis()
    def fail(*_args,**_kwargs):raise BackendError('AI_GATEWAY_UNAVAILABLE')
    monkeypatch.setattr(BackendClient,'explain',fail)
    app=AppTest.from_file(str(APP));app.session_state['analysis']=data;app.run()
    next(b for b in app.button if b.label=='Explicar hallazgos').click().run()
    assert not app.exception
    assert any('resultados deterministas' in w.value for w in app.warning)
    assert app.session_state['analysis']==data
    assert any('IOS-SRV-001' in e.label for e in app.expander)


def test_ui_explanation_and_chat_always_use_registered_analysis_id(monkeypatch):
    data=analysis();calls=[]
    def explain(_self,reference,question=None):calls.append((reference,question));return explanation()
    monkeypatch.setattr(BackendClient,'explain',explain)
    app=AppTest.from_file(str(APP));app.session_state['analysis']=data;app.run()
    next(b for b in app.button if b.label=='Explicar hallazgos').click().run()
    app.chat_input[0].set_value('¿Qué revisar?').run()
    assert not app.exception and calls==[(data['analysis_id'],None),(data['analysis_id'],'¿Qué revisar?')]
    assert app.session_state['analysis']==data


def test_ui_clears_device_credentials_after_submit(monkeypatch):
    monkeypatch.setattr(BackendClient,'analyze_device',lambda *_:analysis())
    app=AppTest.from_file(str(APP)).run();app.radio[0].set_value('Analizar dispositivo').run()
    app.text_input[0].set_value('192.168.50.10')
    app.text_input[1].set_value('synthetic-user')
    app.text_input[2].set_value('SYNTHETIC_PASSWORD_NOT_REAL')
    next(b for b in app.button if b.label=='Analizar dispositivo').click().run()
    assert not app.exception
    assert all(x.value=='' for x in app.text_input)
    assert 'SYNTHETIC_PASSWORD_NOT_REAL' not in json.dumps(app.session_state['analysis'])


def test_ui_backend_client_sends_only_id_and_question_to_explainer():
    seen=[];reference=str(uuid4())
    def handle(request):seen.append(request);return httpx.Response(200,json=explanation())
    client=BackendClient(transport=httpx.MockTransport(handle))
    client.explain(reference,'¿Qué revisar?')
    assert seen[0].url.path==f'/api/v1/analyses/{reference}/ai-explanation'
    assert json.loads(seen[0].content)=={'question':'¿Qué revisar?'}


def test_ui_backend_failures_do_not_echo_response_bodies():
    client=BackendClient(transport=httpx.MockTransport(lambda _:httpx.Response(500,text='SYNTHETIC_VALUE_NOT_TO_EXPOSE')))
    with pytest.raises(BackendError) as exc:client.explain(str(uuid4()))
    assert 'SYNTHETIC' not in str(exc.value)


def test_dependency_boundaries_are_enforced():
    for p in (ROOT/'src/ios_auditor/ai').glob('*.py'):
        tree=ast.parse(p.read_text(encoding='utf-8'))
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):imports.append(node.module or '')
        assert not any('netmiko' in i.lower() or 'collectors' in i or i.startswith('ios_auditor.api') for i in imports)
    for p in [APP,ROOT/'src/ios_auditor/ui/backend.py']:
        assert 'OmniRouteClient' not in p.read_text(encoding='utf-8')
        assert 'ios_auditor.ai' not in p.read_text(encoding='utf-8')
