from __future__ import annotations

import os
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from .errors import AIError, AIErrorCode


class AISettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = False
    base_url: str = "http://127.0.0.1:20128/v1"
    api_key: SecretStr = Field(default=SecretStr(""), repr=False)
    model: str = Field(default="", max_length=160)
    timeout_seconds: float = Field(default=15, ge=0.1, le=120)
    max_retries: int = Field(default=1, ge=0, le=1)

    @field_validator("base_url")
    @classmethod
    def safe_url(cls, value: str) -> str:
        parts = urlsplit(value)
        if (parts.scheme not in {"http", "https"} or not parts.hostname
                or parts.username or parts.password or parts.query or parts.fragment):
            raise ValueError("URL de pasarela no válida.")
        return value.rstrip("/")

    @field_validator("model")
    @classmethod
    def concrete_model(cls, value: str) -> str:
        value = value.strip()
        if value.lower().split("/")[-1] == "auto" or any(c.isspace() for c in value):
            raise ValueError("Debe seleccionar un modelo concreto.")
        return value

    @classmethod
    def from_env(cls) -> AISettings:
        # No carga .env, cookies, archivos de proveedores ni sesiones del navegador.
        try:
            enabled = os.getenv("NETAUDIT_AI_ENABLED", "false").strip().lower()
            if enabled not in {"true", "false", "1", "0"}:
                raise ValueError("Booleano no válido.")
            return cls(
                enabled=enabled in {"true", "1"},
                base_url=os.getenv("NETAUDIT_AI_BASE_URL", "http://127.0.0.1:20128/v1"),
                api_key=SecretStr(os.getenv("NETAUDIT_AI_API_KEY", "")),
                model=os.getenv("NETAUDIT_AI_MODEL", ""),
                timeout_seconds=float(os.getenv("NETAUDIT_AI_TIMEOUT_SECONDS", "15")),
                max_retries=int(os.getenv("NETAUDIT_AI_MAX_RETRIES", "1")),
            )
        except (ValueError, TypeError):
            raise AIError(AIErrorCode.INVALID_RESPONSE) from None
