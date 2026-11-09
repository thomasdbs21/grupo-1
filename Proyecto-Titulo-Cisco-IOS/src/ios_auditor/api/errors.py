from __future__ import annotations

from dataclasses import dataclass


# Error HTTP controlado con un código y mensaje que la API puede publicar.
@dataclass(frozen=True, slots=True)
class ApiError(Exception):
    status_code: int
    code: str
    message: str
