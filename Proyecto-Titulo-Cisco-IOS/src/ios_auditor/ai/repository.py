from collections import OrderedDict
from threading import RLock
from uuid import UUID

from .contracts import AIContext


class AIContextRepository:
    """Solo snapshots inmutables sanitizados; memoria acotada, sin credenciales ni entradas crudas."""

    def __init__(self, max_items: int = 100):
        if max_items < 1:
            raise ValueError("max_items debe ser positivo.")
        self._max_items = max_items
        self._items: OrderedDict[UUID, AIContext] = OrderedDict()
        self._lock = RLock()

    def put(self, context: AIContext) -> None:
        with self._lock:
            self._items[context.analysis_id] = context
            self._items.move_to_end(context.analysis_id)
            while len(self._items) > self._max_items:
                self._items.popitem(last=False)

    def get(self, analysis_id: UUID) -> AIContext | None:
        with self._lock:
            return self._items.get(analysis_id)

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)
