from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError, dataclass, field
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from ios_auditor.collectors import (
    CollectorAuthenticationError,
    CollectorTimeoutError,
    CommandEvidence,
)
from ios_auditor.domain import AnalysisContext, AnalysisResult, RuleStatus
from ios_auditor.rules.pilot import TelnetVtyRule
from ios_auditor.services import (
    CollectedAnalysisContractError,
    CollectedAnalysisResult,
    analyze_collected_running_config,
)


RUNNING_CONFIG_COMMAND = "show running-config"
SOURCE_NAME = "ssh-running-config"
FAKE_HOST = "router.example.invalid"
FAKE_PASSWORD = "CREDENCIAL_FICTICIA_NO_REAL"
RAW_CONFIG = (
    "hostname ROUTER-PRUEBA\r\n"
    "enable password VALOR_FICTICIO\r\n"
    "ip http server\r\n"
    "line vty 0 4\r\n"
    " transport input telnet ssh\r\n"
)


def _evidence(
    *,
    raw_output: str = RAW_CONFIG,
    normalized_output: str | None = None,
    command: str = RUNNING_CONFIG_COMMAND,
    execution_id: UUID | None = None,
    sha256: str | None = None,
) -> CommandEvidence:
    normalized = normalized_output or raw_output.replace("\r\n", "\n")
    return CommandEvidence(
        execution_id=execution_id or uuid4(),
        device_host=FAKE_HOST,
        command=command,
        collected_at=datetime.now(timezone.utc),
        raw_output=raw_output,
        normalized_output=normalized,
        sha256=sha256 or hashlib.sha256(raw_output.encode("utf-8")).hexdigest(),
    )


@dataclass
class FakeCollector:
    evidences: tuple[CommandEvidence, ...] = ()
    error: Exception | None = None
    calls: list[tuple[object, UUID | None]] = field(default_factory=list)
    send_config_set: MagicMock = field(default_factory=MagicMock)
    config_mode: MagicMock = field(default_factory=MagicMock)

    def collect(self, commands, *, execution_id=None):
        self.calls.append((commands, execution_id))
        if self.error is not None:
            raise self.error
        return self.evidences


def _analysis_result(raw: bytes, source_name: str) -> AnalysisResult:
    return AnalysisResult(
        source_path=source_name,
        sha256=hashlib.sha256(raw).hexdigest(),
        evaluations=(),
        findings=(),
    )


def test_requests_only_running_config_once():
    evidence = _evidence()
    collector = FakeCollector((evidence,))

    analyze_collected_running_config(collector)

    assert collector.calls == [(RUNNING_CONFIG_COMMAND, None)]


def test_raw_output_reaches_injected_analyzer_and_normalized_output_is_not_used():
    normalized = "CONTENIDO_NORMALIZADO_QUE_NO_DEBE_ANALIZARSE\n"
    evidence = _evidence(normalized_output=normalized)
    collector = FakeCollector((evidence,))
    analyzer = MagicMock(
        return_value=_analysis_result(evidence.raw_output.encode("utf-8"), SOURCE_NAME)
    )

    analyze_collected_running_config(collector, analyzer=analyzer)

    analyzer.assert_called_once_with(
        evidence.raw_output.encode("utf-8"),
        source_name=SOURCE_NAME,
        registry=None,
    )
    assert analyzer.call_args.args[0] != normalized.encode("utf-8")


def test_source_name_is_constant_and_does_not_contain_host():
    evidence = _evidence()
    analyzer = MagicMock(
        return_value=_analysis_result(evidence.raw_output.encode("utf-8"), SOURCE_NAME)
    )

    analyze_collected_running_config(
        FakeCollector((evidence,)),
        analyzer=analyzer,
    )

    source_name = analyzer.call_args.kwargs["source_name"]
    assert source_name == SOURCE_NAME
    assert evidence.device_host not in source_name


def test_optional_registry_is_forwarded_to_analyzer():
    evidence = _evidence()
    registry = MagicMock()
    analyzer = MagicMock(
        return_value=_analysis_result(evidence.raw_output.encode("utf-8"), SOURCE_NAME)
    )

    analyze_collected_running_config(
        FakeCollector((evidence,)),
        registry=registry,
        analyzer=analyzer,
    )

    assert analyzer.call_args.kwargs["registry"] is registry


def test_result_preserves_evidence_execution_id_and_matching_hashes():
    evidence = _evidence()

    result = analyze_collected_running_config(FakeCollector((evidence,)))

    assert isinstance(result, CollectedAnalysisResult)
    assert result.evidence is evidence
    assert result.execution_id == evidence.execution_id
    assert result.analysis_result.sha256 == evidence.sha256


def test_integrated_flow_executes_all_three_pilot_rules():
    result = analyze_collected_running_config(FakeCollector((_evidence(),)))

    assert len(result.analysis_result.evaluations) == 3
    assert len(result.analysis_result.findings) == 3
    assert all(
        evaluation.status is RuleStatus.FAIL
        for evaluation in result.analysis_result.evaluations
    )


def test_rules_receive_analysis_context_and_never_collector(monkeypatch):
    evidence = _evidence()
    collector = FakeCollector((evidence,))
    received_contexts: list[AnalysisContext] = []
    original_evaluate = TelnetVtyRule.evaluate

    def record_context(self, context):
        received_contexts.append(context)
        return original_evaluate(self, context)

    monkeypatch.setattr(TelnetVtyRule, "evaluate", record_context)

    analyze_collected_running_config(collector)

    assert len(received_contexts) == 1
    assert isinstance(received_contexts[0], AnalysisContext)
    assert received_contexts[0] is not collector


@pytest.mark.parametrize(
    ("evidences", "message"),
    [
        ((), "exactamente una evidencia"),
        ((_evidence(), _evidence()), "exactamente una evidencia"),
        ((_evidence(command="show version"),), "comando inesperado"),
    ],
)
def test_invalid_collection_shape_or_command_is_rejected(evidences, message):
    with pytest.raises(CollectedAnalysisContractError, match=message):
        analyze_collected_running_config(FakeCollector(evidences))


def test_different_requested_execution_id_is_rejected():
    with pytest.raises(CollectedAnalysisContractError, match="identificador"):
        analyze_collected_running_config(
            FakeCollector((_evidence(),)),
            execution_id=uuid4(),
        )


def test_inconsistent_evidence_sha256_is_rejected():
    evidence = _evidence(sha256="0" * 64)

    with pytest.raises(CollectedAnalysisContractError, match="integridad"):
        analyze_collected_running_config(FakeCollector((evidence,)))


def test_inconsistent_analyzer_sha256_is_rejected():
    evidence = _evidence()
    analyzer = MagicMock(
        return_value=AnalysisResult(
            source_path=SOURCE_NAME,
            sha256="0" * 64,
            evaluations=(),
            findings=(),
        )
    )

    with pytest.raises(CollectedAnalysisContractError, match="integridad"):
        analyze_collected_running_config(
            FakeCollector((evidence,)),
            analyzer=analyzer,
        )


@pytest.mark.parametrize(
    "error",
    [
        CollectorAuthenticationError("No fue posible autenticar por SSH."),
        CollectorTimeoutError("La conexion SSH excedio el tiempo permitido."),
    ],
)
def test_safe_collector_errors_are_propagated_unchanged(error):
    collector = FakeCollector(error=error)

    with pytest.raises(type(error)) as captured:
        analyze_collected_running_config(collector)

    assert captured.value is error
    assert FAKE_PASSWORD not in str(captured.value)
    assert RAW_CONFIG not in str(captured.value)


def test_contract_errors_do_not_include_sensitive_values():
    evidence = _evidence(command="COMANDO_SENSIBLE_NO_AUTORIZADO")

    with pytest.raises(CollectedAnalysisContractError) as captured:
        analyze_collected_running_config(FakeCollector((evidence,)))

    message = str(captured.value)
    assert FAKE_HOST not in message
    assert FAKE_PASSWORD not in message
    assert evidence.raw_output not in message
    assert evidence.normalized_output not in message


def test_result_is_immutable():
    result = analyze_collected_running_config(FakeCollector((_evidence(),)))

    with pytest.raises(FrozenInstanceError):
        result.evidence = _evidence()


def test_fake_collector_opens_no_network_and_configuration_methods_are_not_called():
    collector = FakeCollector((_evidence(),))

    analyze_collected_running_config(collector)

    collector.send_config_set.assert_not_called()
    collector.config_mode.assert_not_called()
