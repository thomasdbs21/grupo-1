from __future__ import annotations

from ios_auditor.api.repository import InMemoryAnalysisRepository
from ios_auditor.services.analyzer import analyze_bytes


def test_repository_keeps_creation_order():
    repository = InMemoryAnalysisRepository(max_items=3)
    result = analyze_bytes(b"hostname R1\n", source_name="one.cfg")

    created = [repository.create(source_name=f"{index}.cfg", result=result) for index in range(3)]

    assert repository.list_ids() == tuple(item.analysis_id for item in created)


def test_repository_evicts_oldest_after_one_hundred_items():
    repository = InMemoryAnalysisRepository(max_items=100)
    result = analyze_bytes(b"hostname R1\n", source_name="running.cfg")

    created = [
        repository.create(source_name=f"{index}.cfg", result=result)
        for index in range(101)
    ]

    assert len(repository) == 100
    assert repository.get(created[0].analysis_id) is None
    assert repository.get(created[1].analysis_id) is not None
    assert repository.list_ids()[-1] == created[-1].analysis_id
