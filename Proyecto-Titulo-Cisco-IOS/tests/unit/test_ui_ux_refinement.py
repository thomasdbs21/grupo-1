import copy
import csv
import io
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from ios_auditor.ui.backend import BackendClient, BackendError
from ios_auditor.ui.presentation import csv_export, filtered_findings, json_export, safe_result, service_badges

ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/'apps/streamlit/app.py'

@pytest.fixture
def data():
    return {'analysis_id':str(uuid4()),'total_evaluations':2,'total_findings':2,
        'status_summary':{'FAIL':2},'findings':[
        {'rule_id':'IOS-DOC-001','rule_name':'Documentación','severity':'LOW','message':'Sin descripción',
         'recommendation':'Revisión manual','evidence':[]},
        {'rule_id':'IOS-AUTH-003','rule_name':'Usuario local','severity':'HIGH','message':'Método heredado',
         'recommendation':'Revisión manual','evidence':[{'source':'running-config','sha256':'a'*64,'line_number':2,
         'content':'username lab password SYNTHETIC_SECRET_NOT_REAL'}]}]}

@pytest.fixture
def ui(monkeypatch,data):
    monkeypatch.setattr(BackendClient,'system_status',lambda _:{'backend':True,'engine':True,
        'ai':{'enabled':True,'gateway_reachable':True,'model_configured':True}})
    app=AppTest.from_file(str(APP));app.session_state['analysis']=copy.deepcopy(data)
    return app.run()

def test_filters_search_sort_and_preserve_dto(data):
    before=copy.deepcopy(data)
    assert [f['severity'] for f in filtered_findings(data)]==['HIGH','LOW']
    assert [f['rule_id'] for f in filtered_findings(data,query='ios-auth-003')]==['IOS-AUTH-003']
    assert len(filtered_findings(data,severities=['LOW']))==1
    assert filtered_findings(data,rules=['IOS-UNKNOWN-000'])==[]
    assert data==before

def test_export_drops_credentials_raw_payload_and_redacts_evidence(data):
    data.update(password='SYNTHETIC_CONNECTION_PASSWORD',api_key='SYNTHETIC_API_KEY',
                raw_output='SYNTHETIC_RAW_OUTPUT',host='192.168.50.10')
    data['findings'][0]['api_key']='SYNTHETIC_NESTED_KEY'
    before=copy.deepcopy(data)
    for payload in (json_export(data),csv_export(data)):
        decoded=payload.decode('utf-8-sig')
        for secret in ('SYNTHETIC_CONNECTION_PASSWORD','SYNTHETIC_API_KEY','SYNTHETIC_RAW_OUTPUT',
                       'SYNTHETIC_NESTED_KEY','SYNTHETIC_SECRET_NOT_REAL','192.168.50.10'):
            assert secret not in decoded
        assert '<REDACTED>' in decoded
    assert json.loads(json_export(data))['status_summary']==data['status_summary']
    assert data==before

@pytest.mark.parametrize('value',['=HYPERLINK("https://example.invalid")','+1+1','-1+1','@SUM(A1)','\t=1+1','  =1+1'])
def test_csv_formula_injection_is_neutralized(data,value):
    data['findings'][0]['message']=value
    rows=list(csv.DictReader(io.StringIO(csv_export(data).decode('utf-8-sig'))))
    assert rows[0]['message'].startswith("'")

def test_export_uses_all_findings_regardless_of_filters(data):
    assert len(filtered_findings(data,['HIGH']))==1
    assert len(json.loads(json_export(data))['findings'])==2

def test_health_uses_backend_gets_only_without_inference():
    seen=[]
    def handle(request):
        seen.append((request.method,request.url.path))
        value={'/health':{'status':'ok'},'/api/v1/rules':[{'id':'IOS-SRV-001'}],
            '/api/v1/ai/health':{'enabled':True,'gateway_reachable':True,'model_configured':True,'api_key':'SYNTHETIC_NOT_TO_KEEP'}}[request.url.path]
        return httpx.Response(200,json=value)
    result=BackendClient(transport=httpx.MockTransport(handle)).system_status()
    assert result['backend'] and result['engine'] and result['ai']['gateway_reachable']
    assert 'api_key' not in result['ai']
    assert len(seen)==3 and all(method=='GET' for method,_ in seen)

def test_health_does_not_promote_inference_without_a_response():
    health={'backend':True,'engine':True,'ai':{'enabled':True,'gateway_reachable':True,'model_configured':True}}
    assert service_badges(health)[-1][2]=='warn'
    assert service_badges(health,True)[-1][2]=='ok'
    health['ai']['gateway_reachable']=False
    assert service_badges(health,True)[-1][2]=='error'
    health['ai']['enabled']=False
    assert service_badges(health)[-1][2]=='muted'

def test_new_analysis_clears_result_filters_and_chat_only(ui,tmp_path):
    unrelated=tmp_path/'untouched.txt';unrelated.write_text('keep')
    ui.session_state['chat']=[{'role':'user','content':'Pregunta'}]
    ui.session_state['preference_kept']='keep'
    next(b for b in ui.button if b.label=='Nuevo análisis').click().run()
    assert not ui.exception and 'analysis' not in ui.session_state
    assert 'chat' not in ui.session_state and 'filter_query' not in ui.session_state
    assert ui.session_state['preference_kept']=='keep' and unrelated.read_text()=='keep'

def test_ui_search_and_sanitized_view_do_not_modify_analysis(ui,data):
    search=next(t for t in ui.text_input if t.label=='Buscar hallazgo')
    search.set_value('IOS-AUTH-003').run()
    assert not ui.exception
    assert any('1 de 2 Findings' in c.value for c in ui.caption)
    assert ui.session_state['analysis']==data
    assert all('SYNTHETIC_SECRET_NOT_REAL' not in code.value for code in ui.code)

def test_ui_health_cached_during_filters_without_polling(monkeypatch,data):
    calls=[]
    def status(_):calls.append(1);return {'backend':True,'engine':True,'ai':None}
    monkeypatch.setattr(BackendClient,'system_status',status)
    app=AppTest.from_file(str(APP));app.session_state['analysis']=data;app.run()
    next(t for t in app.text_input if t.label=='Buscar hallazgo').set_value('auth').run()
    assert not app.exception and len(calls)==1

def test_chat_stores_sanitized_question_and_handles_gateway_failure(ui,monkeypatch,data):
    seen=[]
    def fail(_self,reference,question=None):seen.append((reference,question));raise BackendError('AI_GATEWAY_UNAVAILABLE')
    monkeypatch.setattr(BackendClient,'explain',fail)
    ui.chat_input[0].set_value('password=SYNTHETIC_SECRET_NOT_REAL').run()
    assert not ui.exception and '<REDACTED>' in seen[0][1]
    assert 'chat' not in ui.session_state or 'SYNTHETIC_SECRET_NOT_REAL' not in json.dumps(ui.session_state['chat'])
    assert ui.session_state['analysis']==data
    assert any('resultados deterministas' in w.value for w in ui.warning)
