"""assistant API 테스트."""

from server.app.api.http.routes.assistant import chat as assistant_chat_routes
from server.app.domain.retrieval import RetrievalSearchResult


class _FakeAssistantChatService:
    def __init__(self):
        self.calls = []

    def answer(self, **kwargs):
        self.calls.append(kwargs)
        return type(
            "AssistantResult",
            (),
            {
                "query": kwargs["query"],
                "answer": "결정된 다음 할 일은 온보딩 자료 공유입니다. [S1]",
                "sources": [
                    RetrievalSearchResult(
                        chunk_id="chunk-1",
                        document_id="doc-1",
                        source_type="report",
                        source_id="source-1",
                        document_title="고객 온보딩 회의록",
                        chunk_text="온보딩 자료는 다음 주까지 공유하기로 했다.",
                        chunk_heading="결정 사항",
                        distance=0.12,
                        session_id="session-1",
                        report_id="report-1",
                    )
                ],
            },
        )()


def test_assistant_chat_api가_답변과_근거를_반환한다(client, monkeypatch) -> None:
    fake_service = _FakeAssistantChatService()
    monkeypatch.setattr(
        assistant_chat_routes,
        "get_assistant_chat_service",
        lambda: fake_service,
    )

    response = client.post(
        "/api/v1/assistant/chat",
        json={
            "query": "다음 할 일은?",
            "source_types": ["report"],
            "session_id": "session-1",
            "limit": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "다음 할 일은?"
    assert payload["answer"].startswith("결정된 다음 할 일")
    assert payload["source_count"] == 1
    assert payload["sources"][0]["chunk_heading"] == "결정 사항"
    assert fake_service.calls[0]["source_types"] == ("report",)
    assert fake_service.calls[0]["session_id"] == "session-1"
    assert fake_service.calls[0]["limit"] == 3


def test_assistant_chat_api는_빈_질문을_거절한다(client) -> None:
    response = client.post("/api/v1/assistant/chat", json={"query": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "질문을 입력해 주세요."
