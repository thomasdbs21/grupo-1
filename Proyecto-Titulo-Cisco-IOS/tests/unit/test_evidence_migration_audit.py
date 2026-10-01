"""Auditoría transversal del contrato; no abre conexiones ni usa el router."""

from typing import get_args

import pytest

from ios_auditor.api.schemas import CanonicalCommand, FullDeviceAnalysisResponse
from ios_auditor.api.full_device_serialization import to_full_device_analysis_response
from ios_auditor.collectors import ALLOWED_COMMANDS
from ios_auditor.parsers.show_commands import SUPPORTED_SHOW_COMMANDS
from ios_auditor.services import CANONICAL_EVIDENCE_COMMANDS
from test_operational_expansion import outputs
from unittest.mock import Mock
from ios_auditor.services import collect_and_analyze_device


def test_all_eight_command_consumers_agree():
    commands = CANONICAL_EVIDENCE_COMMANDS
    assert len(commands) == len(set(commands)) == 8
    assert ALLOWED_COMMANDS == frozenset(commands)
    assert get_args(CanonicalCommand) == commands
    assert tuple(SUPPORTED_SHOW_COMMANDS) == commands[1:]
    schema = FullDeviceAnalysisResponse.model_json_schema()
    field = schema["properties"]["evidences"]
    assert field["minItems"] == field["maxItems"] == len(commands)


def test_public_response_rejects_historical_four_evidence_payload():
    connection = Mock()
    connection.send_command.side_effect = outputs().__getitem__
    result = collect_and_analyze_device(
        host="synthetic.example.invalid", port=22, username="<REDACTED>",
        password="<REDACTED>", connection_factory=Mock(return_value=connection),
    )
    response = to_full_device_analysis_response(result).model_dump()
    response["evidences"] = response["evidences"][:4]
    with pytest.raises(ValueError):
        FullDeviceAnalysisResponse.model_validate(response)
    connection.disconnect.assert_called_once_with()
