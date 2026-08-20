from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError

import pytest

from ios_auditor.services.analyzer import AnalysisError, load_context


def test_sha256_is_calculated_from_original_bytes(tmp_path):
    content = "hostname R1\nline vty 0 4\n transport input ssh\n"
    path = tmp_path / "running.cfg"
    path.write_text(content, encoding="utf-8")

    context = load_context(path)

    assert context.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(AnalysisError, match="no existe"):
        load_context(tmp_path / "missing.cfg")


def test_empty_file_is_rejected(tmp_path):
    path = tmp_path / "empty.cfg"
    path.write_text("  \n", encoding="utf-8")

    with pytest.raises(AnalysisError, match="vacío"):
        load_context(path)


def test_parser_builds_normalized_vty_sections(tmp_path):
    path = tmp_path / "running.cfg"
    path.write_text(
        "hostname R1\nline vty 0 4\n transport input ssh\n",
        encoding="utf-8",
    )

    context = load_context(path)

    assert context.vty_sections[0].header == "line vty 0 4"
    assert context.vty_sections[0].transport_inputs[0][1] == ("ssh",)


def test_context_is_immutable(tmp_path):
    path = tmp_path / "running.cfg"
    path.write_text("hostname R1\n", encoding="utf-8")
    context = load_context(path)

    with pytest.raises(FrozenInstanceError):
        context.sha256 = "changed"
