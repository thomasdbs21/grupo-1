import json
from uuid import uuid4
from dataclasses import replace

import httpx
import pytest
from pydantic import SecretStr

from ios_auditor.ai.client import MAX_RESPONSE_BYTES, OmniRouteClient
from ios_auditor.ai.contracts import Explanation
from ios_auditor.ai.errors import AIError, AIErrorCode
from ios_auditor.ai.service import ExplanationService, build_context
from ios_auditor.ai.settings import AISettings
from ios_auditor.domain import Evidence, Finding, Severity


def context():
    return build_context(uuid4(), (Finding("IOS-SRV-001", "HTTP", Severity.HIGH,
        "HTTP habilitado", "Revisar el servicio", (Evidence("running-config", "a"*64, 1, "ip http server"),)),))


def answer(rule_id="IOS-SRV-001"):
    return dict(summary="El servicio requiere revisión manual.", findings=[dict(rule_id=rule_id,
        explanation="La evidencia indica HTTP habilitado.", technical_impact="Tráfico sin cifrar.",
        priority_reason="Se utiliza la severidad del motor.", manual_review="Revisar manualmente show running-config.")],
        limitations=["No demuestra exposición externa."], question_answer="Verificar la evidencia del servicio.")


def settings(**kwargs):return AISettings(enabled=True, model="synthetic/free-model", **kwargs)


@pytest.mark.parametrize("status,code,calls", [
    (400, AIErrorCode.MODEL_UNAVAILABLE, 1), (404, AIErrorCode.MODEL_UNAVAILABLE, 1),
    (401, AIErrorCode.AUTH_ERROR, 1), (403, AIErrorCode.AUTH_ERROR, 1),
    (429, AIErrorCode.RATE_LIMITED, 2), (500, AIErrorCode.UPSTREAM_ERROR, 2),
    (503, AIErrorCode.UPSTREAM_ERROR, 2),
])
def test_http_errors_are_mapped_without_leaking_or_unbounded_retries(status, code, calls, caplog):
    requests = []
    def handle(request):
        requests.append(request)
        return httpx.Response(status, json={"error": "SYNTHETIC_UPSTREAM_SECRET_NOT_REAL"})
    client = OmniRouteClient(settings(api_key=SecretStr("SYNTHETIC_KEY_NOT_REAL")), transport=httpx.MockTransport(handle), sleep=lambda _: None)
    with pytest.raises(AIError) as exc:client.complete([])
    assert exc.value.code == code and len(requests) == calls
    assert "SYNTHETIC" not in str(exc.value) and "SYNTHETIC" not in caplog.text
    assert requests[0].headers["authorization"] == "Bearer SYNTHETIC_KEY_NOT_REAL"


@pytest.mark.parametrize("error,code,calls", [(httpx.ConnectError, AIErrorCode.GATEWAY_UNAVAILABLE, 1),
    (httpx.ReadTimeout, AIErrorCode.TIMEOUT, 2), (httpx.ConnectTimeout, AIErrorCode.TIMEOUT, 2)])
def test_network_errors_are_controlled(error, code, calls):
    seen=[]
    def handle(request):seen.append(request);raise error("SYNTHETIC_NOT_TO_EXPOSE", request=request)
    client=OmniRouteClient(settings(),transport=httpx.MockTransport(handle),sleep=lambda _:None)
    with pytest.raises(AIError) as exc:client.complete([])
    assert exc.value.code==code and len(seen)==calls
    assert "SYNTHETIC" not in str(exc.value)


def test_success_sends_only_chat_completions_and_no_tools():
    seen=[]
    def handle(request):
        seen.append(request)
        return httpx.Response(200,json={"choices":[{"message":{"content":"{}"}}]})
    client=OmniRouteClient(settings(),transport=httpx.MockTransport(handle))
    assert client.complete([{"role":"user","content":"datos"}])=="{}"
    payload=json.loads(seen[0].content)
    assert seen[0].url.path=="/v1/chat/completions"
    assert payload["stream"] is False and payload["model"]=="synthetic/free-model"
    assert not any(k in payload for k in ["tools","tool_choice","functions"])


def test_disabled_or_missing_model_never_makes_a_request():
    def fail(_):raise AssertionError("No debe haber red")
    for config,code in [(AISettings(),AIErrorCode.DISABLED),(AISettings(enabled=True),AIErrorCode.MODEL_UNAVAILABLE)]:
        client=OmniRouteClient(config,transport=httpx.MockTransport(fail))
        with pytest.raises(AIError) as exc:client.complete([])
        assert exc.value.code==code
    assert OmniRouteClient(AISettings(),transport=httpx.MockTransport(fail)).reachable() is False


@pytest.mark.parametrize("payload", [{}, {"choices":[]}, {"choices":[{"message":{"content":None}}]}])
def test_invalid_outer_payload_is_not_exposed(payload):
    client=OmniRouteClient(settings(),transport=httpx.MockTransport(lambda _:httpx.Response(200,json=payload)))
    with pytest.raises(AIError) as exc:client.complete([])
    assert exc.value.code==AIErrorCode.INVALID_RESPONSE


def test_oversized_provider_payload_is_rejected():
    client=OmniRouteClient(settings(),transport=httpx.MockTransport(lambda _:httpx.Response(200,content=b'x'*(MAX_RESPONSE_BYTES+1))))
    with pytest.raises(AIError) as exc:client.complete([])
    assert exc.value.code==AIErrorCode.INVALID_RESPONSE


class Fake:
    def __init__(self, *answers):self.answers=list(answers);self.calls=[]
    def complete(self,messages):self.calls.append(messages);return self.answers.pop(0)
    def reachable(self):return True


def test_valid_explanation_and_question_preserve_deterministic_context():
    source=context();before=source.model_dump_json()
    fake=Fake(json.dumps(answer()))
    result=ExplanationService(settings(),fake).explain(source,"¿Qué revisar?")
    assert result.source=="ai" and result.explanation.question_answer
    assert source.model_dump_json()==before
    assert source.findings[0].severity=="HIGH" and source.findings[0].evidence==( "ip http server",)
    assert len(fake.calls)==1 and "¿Qué revisar?" in fake.calls[0][1]["content"]


@pytest.mark.parametrize("bad", ["not JSON", '{"summary":"falta contrato"}', json.dumps({**answer(),"severity":"LOW"})])
def test_json_or_schema_failure_allows_one_repair_only(bad):
    fake=Fake(bad,bad)
    with pytest.raises(AIError) as exc:ExplanationService(settings(),fake).explain(context())
    assert exc.value.code==AIErrorCode.INVALID_RESPONSE and len(fake.calls)==2
    assert bad not in fake.calls[1][-1]["content"]


def test_single_repair_can_succeed():
    fake=Fake("not JSON",json.dumps(answer()))
    assert ExplanationService(settings(),fake).explain(context()).source=="ai"
    assert len(fake.calls)==2


@pytest.mark.parametrize("kind", ["invented", "duplicate", "missing"])
def test_invented_duplicate_or_missing_references_are_rejected_without_repair(kind):
    data=answer("IOS-FAKE-999" if kind=="invented" else "IOS-SRV-001")
    if kind=="duplicate":data["findings"]*=2
    if kind=="missing":data["findings"]=[]
    fake=Fake(json.dumps(data))
    with pytest.raises(AIError) as exc:ExplanationService(settings(),fake).explain(context())
    assert exc.value.code==AIErrorCode.INVALID_RESPONSE and len(fake.calls)==1


def test_configuration_commands_in_explanation_are_rejected():
    data=answer();data["findings"][0]["manual_review"]="configure terminal"
    with pytest.raises(AIError):ExplanationService(settings(),Fake(json.dumps(data))).explain(context())


def test_no_findings_is_deterministic_even_when_ai_disabled():
    fake=Fake();empty=build_context(uuid4(),())
    result=ExplanationService(AISettings(),fake).explain(empty)
    assert result.source=="deterministic" and not result.explanation.findings and not fake.calls


def test_output_secret_echo_is_redacted():
    data=answer();data["summary"]="password=SYNTHETIC_ECHO_NOT_REAL"
    result=ExplanationService(settings(),Fake(json.dumps(data))).explain(context())
    assert "SYNTHETIC_ECHO_NOT_REAL" not in result.model_dump_json()


@pytest.mark.parametrize("kwargs", [{"model":"auto"},{"model":"oc/auto"},{"max_retries":2},{"timeout_seconds":0},{"base_url":"http://user:secret@localhost/v1"},{"base_url":"http://localhost/v1?token=x"}])
def test_unsafe_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):AISettings(**kwargs)


def test_env_settings_are_opt_in_and_hide_key(monkeypatch):
    for name in ["NETAUDIT_AI_ENABLED","NETAUDIT_AI_MODEL","NETAUDIT_AI_API_KEY"]:monkeypatch.delenv(name,raising=False)
    assert AISettings.from_env().enabled is False
    monkeypatch.setenv("NETAUDIT_AI_API_KEY","SYNTHETIC_KEY_NOT_REAL")
    assert "SYNTHETIC" not in repr(AISettings.from_env())
    monkeypatch.setenv("NETAUDIT_AI_MAX_RETRIES","999")
    with pytest.raises(AIError):AISettings.from_env()
