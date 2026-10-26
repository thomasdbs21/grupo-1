from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlsplit

import httpx


class BackendError(Exception):
    def __init__(self, code: str = "BACKEND_UNAVAILABLE"):
        self.code = code
        super().__init__("No fue posible completar la solicitud a NetAudit.")


class BackendClient:
    """No conoce proveedores de IA, prompts, Findings editables ni comandos de dispositivos."""

    def __init__(self, base_url: str | None = None, *, transport: httpx.BaseTransport | None = None):
        self.base_url = (base_url or os.getenv("NETAUDIT_API_BASE_URL", "http://127.0.0.1:8000")).rstrip("/")
        url = urlsplit(self.base_url)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise BackendError("INVALID_API_URL")
        self.transport = transport

    def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        try:
            with httpx.Client(timeout=120, transport=self.transport, trust_env=False,
                              follow_redirects=False) as client:
                response = client.request(method, self.base_url + path, **kwargs)
            if response.is_error:
                code = response.json().get("error", {}).get("code", "BACKEND_ERROR")
                raise BackendError(code if isinstance(code, str) and len(code) < 80 else "BACKEND_ERROR")
            result = response.json()
            if not isinstance(result, dict):
                raise BackendError("INVALID_BACKEND_RESPONSE")
            return result
        except (httpx.HTTPError, ValueError, TypeError):
            raise BackendError() from None

    def analyze_file(self, filename: str, content: bytes) -> dict:
        return self._request("POST", "/api/v1/analyses", files={"file": (filename, content, "application/octet-stream")})

    def analyze_device(self, host: str, port: int, username: str, password: str) -> dict:
        # Las credenciales son transitorias y no se incorporan al estado de análisis de la UI.
        payload = dict(host=host, port=port, username=username, password=password)
        try:
            return self._request("POST", "/api/v1/device-analyses", json=payload)
        finally:
            payload.clear()

    def explain(self, analysis_id: str, question: str | None = None) -> dict:
        from uuid import UUID
        try:
            reference = str(UUID(analysis_id))
        except (ValueError, TypeError):
            raise BackendError("INVALID_ANALYSIS_ID") from None
        return self._request("POST", f"/api/v1/analyses/{reference}/ai-explanation",
                             json={"question": question} if question is not None else {})
