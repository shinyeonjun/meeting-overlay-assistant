"""OpenAI 호환 completion client 테스트."""

from __future__ import annotations

import json

from server.app.services.analysis.llm.clients.openai_compatible_completion_client import (
    OpenAICompatibleCompletionClient,
)


class TestOpenAICompatibleCompletionClient:
    """로컬 OpenAI 호환 completion client를 검증한다."""

    def test_chat_completions_응답에서_message_content를_추출한다(self):
        transport = StubUrlopen(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"candidates":[{"event_type":"question","title":"사파리 이슈 확인","state":"open","priority":70,"body":null,"assignee":null,"due_date":null,"topic_group":null}]}'
                        }
                    }
                ]
            }
        )
        client = OpenAICompatibleCompletionClient(
            model="phi-local",
            base_url="http://127.0.0.1:11434/v1",
            timeout_seconds=7.0,
            urlopen_func=transport,
        )

        result = client.complete("질문 이벤트를 뽑아라")

        assert '"event_type":"question"' in result
        assert transport.last_request is not None
        assert transport.last_timeout == 7.0
        assert transport.last_request.full_url == "http://127.0.0.1:11434/v1/chat/completions"
        assert transport.last_request.headers["Content-type"] == "application/json"
        payload = json.loads(transport.last_request.data.decode("utf-8"))
        assert payload["model"] == "phi-local"
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["content"] == "질문 이벤트를 뽑아라"

    def test_content가_배열이어도_text를_이어붙여_반환한다(self):
        transport = StubUrlopen(
            {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "text", "text": '{"candidates":['},
                                {"type": "text", "text": ']}'},
                            ]
                        }
                    }
                ]
            }
        )
        client = OpenAICompatibleCompletionClient(
            model="phi-local",
            base_url="http://127.0.0.1:11434/v1",
            urlopen_func=transport,
        )

        result = client.complete("응답 테스트")

        assert result == '{"candidates":[]}'


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
