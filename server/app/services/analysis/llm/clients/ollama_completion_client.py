"""공통 영역의 ollama completion client 서비스를 제공한다."""
from __future__ import annotations

import json
from typing import Any, Callable
from urllib import request

from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)


class OllamaCompletionClient(LLMCompletionClient):
    """Ollama native API를 직접 호출한다."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434/v1",
        timeout_seconds: float = 20.0,
        urlopen_func: Callable[..., Any] | None = None,
    ) -> None:
        self._model = model
        self._base_url = self._to_native_base_url(base_url)
        self._timeout_seconds = timeout_seconds
        self._urlopen = urlopen_func or request.urlopen

    def complete(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        response_schema: dict[str, Any] | None = None,
        keep_alive: str | None = None,
    ) -> str:
        """Ollama native chat API를 호출해 문자열 응답을 반환한다."""

        payload: dict[str, Any] = {
            "model": self._model,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt or "너는 회의 발화를 구조화하는 분석기다. 반드시 JSON만 반환한다.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "options": {
                "temperature": 0,
            },
        }
        if response_schema is not None:
            payload["format"] = response_schema
        if keep_alive is not None:
            payload["keep_alive"] = keep_alive
        response_payload = self._post_json(f"{self._base_url}/api/chat", payload)
        message = response_payload.get("message", {})
        content = message.get("content", "")
        return content if isinstance(content, str) else ""

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        req = request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with self._urlopen(req, timeout=self._timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _to_native_base_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/v1"):
            normalized = normalized[:-3]
        return normalized.rstrip("/")
