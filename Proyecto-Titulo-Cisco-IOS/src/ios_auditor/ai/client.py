from __future__ import annotations

import time
from collections.abc import Callable

import httpx

from .errors import AIError, AIErrorCode
from .settings import AISettings

MAX_RESPONSE_BYTES = 128 * 1024


def _status_error(status: int) -> AIError:
    if status in {401, 403}:
        return AIError(AIErrorCode.AUTH_ERROR)
    if status in {400, 404}:
        return AIError(AIErrorCode.MODEL_UNAVAILABLE)
    if status == 429:
        return AIError(AIErrorCode.RATE_LIMITED)
    return AIError(AIErrorCode.UPSTREAM_ERROR)


class OmniRouteClient:
    """HTTP acotado, sin herramientas, routing automático, streaming de tokens ni acceso a red Cisco."""

    def __init__(self, settings: AISettings, *, transport: httpx.BaseTransport | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        self.settings = settings
        self._transport = transport
        self._sleep = sleep

    def _headers(self) -> dict[str, str]:
        key = self.settings.api_key.get_secret_value()
        return {"Authorization": "Bearer " + key} if key else {}

    def complete(self, messages: list[dict[str, str]]) -> str:
        if not self.settings.enabled:
            raise AIError(AIErrorCode.DISABLED)
        if not self.settings.model:
            raise AIError(AIErrorCode.MODEL_UNAVAILABLE)
        for attempt in range(self.settings.max_retries + 1):
            try:
                return self._complete_once(messages)
            except AIError as exc:
                if (attempt == self.settings.max_retries or exc.code not in {
                    AIErrorCode.TIMEOUT, AIErrorCode.RATE_LIMITED, AIErrorCode.UPSTREAM_ERROR
                }):
                    raise
                self._sleep(0.1)
        raise AIError(AIErrorCode.UPSTREAM_ERROR)  # rango validado por settings

    def _complete_once(self, messages: list[dict[str, str]]) -> str:
        try:
            with httpx.Client(timeout=self.settings.timeout_seconds, transport=self._transport,
                              trust_env=False, follow_redirects=False) as client:
                with client.stream("POST", self.settings.base_url + "/chat/completions",
                                   headers=self._headers(), json={
                                       "model": self.settings.model, "messages": messages,
                                       "temperature": 0, "max_tokens": 4000, "stream": False,
                                   }) as response:
                    if response.status_code != 200:
                        raise _status_error(response.status_code)
                    chunks = bytearray()
                    for chunk in response.iter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > MAX_RESPONSE_BYTES:
                            raise AIError(AIErrorCode.INVALID_RESPONSE)
                    import json
                    payload = json.loads(chunks)
                    text = payload["choices"][0]["message"]["content"]
                    if not isinstance(text, str) or not text.strip():
                        raise AIError(AIErrorCode.INVALID_RESPONSE)
                    return text
        except httpx.TimeoutException:
            raise AIError(AIErrorCode.TIMEOUT) from None
        except httpx.TransportError:
            raise AIError(AIErrorCode.GATEWAY_UNAVAILABLE) from None
        except (ValueError, KeyError, IndexError, TypeError):
            raise AIError(AIErrorCode.INVALID_RESPONSE) from None

    def reachable(self) -> bool:
        """Respuesta HTTP no implica inferencia ni acceso al modelo."""
        if not self.settings.enabled:
            return False
        try:
            with httpx.Client(timeout=min(self.settings.timeout_seconds, 2), transport=self._transport,
                              trust_env=False, follow_redirects=False) as client:
                client.get(self.settings.base_url + "/models", headers=self._headers())
            return True
        except httpx.HTTPError:
            return False
