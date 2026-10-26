"""Lotes reproducibles de fixtures SINTÉTICAS; no importa ni invoca transporte SSH."""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from uuid import uuid4

from ios_auditor.collectors import CommandEvidence
from ios_auditor.domain import FullDeviceAnalysisResult
from ios_auditor.services import (
    CANONICAL_EVIDENCE_COMMANDS, analyze_validated_evidence_batch,
    validate_evidence_batch,
)


def analyze_synthetic_scenario(project: Path, filename: str) -> FullDeviceAnalysisResult:
    key = filename.removeprefix("escenario_").removesuffix(".cfg")
    root = project / "samples" / "evaluacion_2"
    outputs = {
        "show running-config": (root / filename).read_text(encoding="utf-8"),
        "show version": "Cisco IOS XE Software, Version 16.09.05\n",
        "show ip ssh": "SSH Enabled - version 2.0\n",
    }
    for command in CANONICAL_EVIDENCE_COMMANDS:
        if command not in outputs:
            path = root / "operacional" / key / (command.replace(" ", "_").replace("-", "_") + ".txt")
            outputs[command] = path.read_text(encoding="utf-8")
    execution_id = uuid4()
    timestamp = datetime.now(timezone.utc)
    batch = validate_evidence_batch(tuple(
        CommandEvidence(execution_id, "synthetic.example.invalid", command,
                        timestamp, outputs[command], outputs[command],
                        hashlib.sha256(outputs[command].encode("utf-8")).hexdigest())
        for command in CANONICAL_EVIDENCE_COMMANDS
    ))
    return analyze_validated_evidence_batch(batch)
