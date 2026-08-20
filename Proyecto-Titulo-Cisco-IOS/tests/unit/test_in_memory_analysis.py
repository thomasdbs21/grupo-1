from __future__ import annotations

import hashlib

import pytest

from ios_auditor.services.analyzer import (
    EmptyContentError,
    InvalidEncodingError,
    analyze_bytes,
    load_context_from_bytes,
)


def test_analysis_from_memory_hashes_exact_received_bytes():
    raw = b"\xef\xbb\xbfhostname R1\nline vty 0 4\n transport input ssh\n"

    result = analyze_bytes(raw, source_name="running.cfg")

    assert result.sha256 == hashlib.sha256(raw).hexdigest()
    assert {finding.rule_id for finding in result.findings} == {
        "IOS-NTP-001",
        "IOS-LOG-001",
    }


def test_analysis_from_memory_accepts_utf8_bom():
    context = load_context_from_bytes(
        b"\xef\xbb\xbfhostname R1\n", source_name="running.cfg"
    )
    assert context.normalized_lines[0] == "hostname R1"


def test_analysis_from_memory_rejects_empty_content():
    with pytest.raises(EmptyContentError):
        analyze_bytes(b" \r\n", source_name="running.cfg")


def test_analysis_from_memory_rejects_binary_content():
    with pytest.raises(InvalidEncodingError):
        analyze_bytes(b"hostname\x00R1", source_name="running.cfg")
