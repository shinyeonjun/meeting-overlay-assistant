"""공통 영역의 test ollama completion client 동작을 검증한다."""
from __future__ import annotations

import json

from server.app.services.analysis.llm.clients.ollama_completion_client import (
    OllamaCompletionClient,
)


class TestOllamaCompletionClient:
    """Ollama native chat API payload를 검증한다."""

    def test_native_chat_api로_schema와_keep_alive를_보낸다(self):
        transport = StubUrlopen(
            {
                "message": {
                    "content": '{"operations":[]}',
                }
            }
        )
        client = OllamaCompletionClient(
            model="qwen2.5:3b-instruct",
            base_url="http://127.0.0.1:11434/v1",
            timeout_seconds=9.0,
            urlopen_func=transport,
        )

        result = client.complete(
            "질문 분석",
            system_prompt="질문만 추출해라",
            response_schema={
                "type": "object",
                "properties": {"operations": {"type": "array"}},
                "required": ["operations"],
                "additionalProperties": False,
            },
            keep_alive="30m",
        )

        assert result == '{"operations":[]}'
        assert transport.last_request.full_url == "http://127.0.0.1:11434/api/chat"
        assert transport.last_timeout == 9.0
        payload = json.loads(transport.last_request.data.decode("utf-8"))
        assert payload["model"] == "qwen2.5:3b-instruct"
        assert payload["messages"][0]["content"] == "질문만 추출해라"
        assert payload["format"]["required"] == ["operations"]
        assert payload["keep_alive"] == "30m"
        assert payload["options"]["temperature"] == 0


class StubUrlopen:
    """urllib.urlopen 대체용 테스트 스텁."""

    def __init__(self, response_payload: dict) -> None:
        self._response_payload = response_payload
        self.last_request = None
        self.last_timeout = None

    def __call__(self, request, timeout=None):
        self.last_request = request
        self.last_timeout = timeout
        return StubResponse(self._response_payload)


class StubResponse:
    """HTTP 응답 객체 스텁."""

    def __init__(self, response_payload: dict) -> None:
        self._response_payload = response_payload

    def __enter__(self) -> "StubResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._response_payload).encode("utf-8")
