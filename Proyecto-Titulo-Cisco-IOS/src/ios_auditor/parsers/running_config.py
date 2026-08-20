from __future__ import annotations

from pathlib import Path

from ciscoconfparse2 import CiscoConfParse

from ios_auditor.domain import AnalysisContext, VtySection


def _line_number(lines: tuple[str, ...], target: str, start: int = 0) -> int:
    normalized_target = target.strip()
    for index in range(start, len(lines)):
        if lines[index].strip() == normalized_target:
            return index + 1
    return 0


def parse_running_config(
    *, source_path: Path, content: str, sha256: str
) -> AnalysisContext:
    raw_lines = tuple(content.splitlines())
    parse = CiscoConfParse(list(raw_lines), syntax="ios")
    normalized_lines = tuple(line.strip() for line in raw_lines if line.strip())

    vty_sections: list[VtySection] = []
    search_start = 0
    for section in parse.find_objects(r"^line vty\s+"):
        header = section.text.strip()
        header_line = _line_number(raw_lines, header, search_start)
        if header_line:
            search_start = header_line

        transports: list[tuple[int, tuple[str, ...]]] = []
        child_start = max(header_line, 0)
        for child in section.children:
            child_text = child.text.strip()
            if not child_text.startswith("transport input "):
                continue
            protocols = tuple(child_text.removeprefix("transport input ").split())
            child_line = _line_number(raw_lines, child_text, child_start)
            transports.append((child_line, protocols))

        vty_sections.append(
            VtySection(
                header=header,
                header_line_number=header_line,
                transport_inputs=tuple(transports),
            )
        )

    return AnalysisContext(
        source_path=str(source_path),
        sha256=sha256,
        original_content=content,
        normalized_lines=normalized_lines,
        vty_sections=tuple(vty_sections),
    )
