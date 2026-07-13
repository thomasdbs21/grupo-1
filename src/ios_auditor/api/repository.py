from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from uuid import UUID, uuid4

from ios_auditor.domain import AnalysisResult


@dataclass(frozen=True, slots=True)
class StoredAnalysis:
    analysis_id: UUID
    source_name: str
    created_at: datetime
    status: str
    result: AnalysisResult


class InMemoryAnalysisRepository:
    """Repositorio temporal, concurrente y no persistente de hasta 100 análisis."""

    def __init__(self, max_items: int = 100) -> None:
        if max_items < 1:
            raise ValueError("max_items debe ser mayor que cero.")
        self._max_items = max_items
        self._items: OrderedDict[UUID, StoredAnalysis] = OrderedDict()
        self._lock = RLock()

    def create(self, *, source_name: str, result: AnalysisResult) -> StoredAnalysis:
        stored = StoredAnalysis(
            analysis_id=uuid4(),
            source_name=source_name,
            created_at=datetime.now(timezone.utc),
            status="COMPLETED",
            result=result,
        )
        with self._lock:
            self._items[stored.analysis_id] = stored
            while len(self._items) > self._max_items:
                self._items.popitem(last=False)
        return stored

    def get(self, analysis_id: UUID) -> StoredAnalysis | None:
        with self._lock:
            return self._items.get(analysis_id)

    def list_ids(self) -> tuple[UUID, ...]:
        with self._lock:
            return tuple(self._items)

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)
