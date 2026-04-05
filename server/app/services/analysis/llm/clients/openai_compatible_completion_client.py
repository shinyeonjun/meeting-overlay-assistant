"""로컬 OpenAI 호환 서버용 completion client."""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib import request

from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)


class OpenAICompatibleCompletionClient(LLMCompletionClient):
    """OpenAI 호환 HTTP 서버에 프롬프트를 보내고 문자열 응답을 받는다."""

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: float = 20.0,
        urlopen_func: Callable[..., Any] | None = None,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
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
        """OpenAI 호환 chat completions 엔드포인트를 호출한다."""
        payload = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt or "너는 회의 발화를 구조화하는 분석기다. 반드시 JSON만 반환한다.",
                },
                {"role": "user", "content": prompt},
            ],
        }
        if response_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "strict": True,
                    "schema": response_schema,
                },
            }
        if keep_alive is not None:
            payload["keep_alive"] = keep_alive
        response_payload = self._post_json("/chat/completions", payload)
        choices = response_payload.get("choices", [])
        if not choices:
            return ""

        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_fragments = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            return "".join(text_fragments)

        return ""

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        req = request.Request(
            url=f"{self._base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with self._urlopen(req, timeout=self._timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
