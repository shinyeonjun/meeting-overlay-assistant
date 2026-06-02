"""assistant API 테스트."""

from types import SimpleNamespace

from server.app.api.http.routes.assistant import chat as assistant_chat_routes
from server.app.domain.retrieval import RetrievalSearchResult


class _FakeAssistantChatService:
    def __init__(self):
        self.calls = []

    def get_conversation_messages(self, **kwargs):
        self.calls.append({"get_conversation_messages": kwargs})
        return (
            SimpleNamespace(
                id=kwargs["conversation_id"],
                title="Decision follow-up",
                status="active",
            ),
            [
                SimpleNamespace(
                    id="message-user-1",
                    role="user",
                    content="What was decided?",
                    status="completed",
                    error_message=None,
                    sources_json=[],
                    metadata_json={},
                    created_at="2026-05-27T00:00:00+00:00",
                    updated_at="2026-05-27T00:00:00+00:00",
                ),
                SimpleNamespace(
                    id="message-assistant-1",
                    role="assistant",
                    content="The proposal will be shared by Friday. [S1]",
                    status="completed",
                    error_message=None,
                    sources_json=[
                        {
                            "chunk_id": "chunk-1",
                            "source_type": "note",
                            "document_title": "7 minute test meeting",
                        }
                    ],
                    metadata_json={"job_id": "job-1"},
                    created_at="2026-05-27T00:00:01+00:00",
                    updated_at="2026-05-27T00:00:02+00:00",
                ),
            ],
        )

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


class _FakeAssistantResponseJobService:
    def __init__(self):
        self.calls = []

    def submit_question(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            conversation=SimpleNamespace(id="conversation-job-1"),
            user_message=SimpleNamespace(id="message-user-1"),
            assistant_message=SimpleNamespace(id="message-assistant-1"),
            job=SimpleNamespace(id="job-1"),
            dispatched=True,
        )


def test_assistant_chat_api_submits_response_job(client, monkeypatch) -> None:
    fake_chat_service = _FakeAssistantChatService()
    fake_job_service = _FakeAssistantResponseJobService()
    monkeypatch.setattr(
        assistant_chat_routes,
        "get_assistant_chat_service",
        lambda: fake_chat_service,
    )
    monkeypatch.setattr(
        assistant_chat_routes,
        "get_assistant_response_job_service",
        lambda: fake_job_service,
    )

    response = client.post(
        "/api/v1/assistant/chat",
        json={
            "query": "What was decided?",
            "conversation_id": "conversation-1",
            "source_types": ["report", "note"],
            "limit": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["conversation_id"] == "conversation-job-1"
    assert payload["message_id"] == "message-assistant-1"
    assert payload["job_id"] == "job-1"
    assert payload["answer"] == ""
    assert fake_chat_service.calls == []
    assert fake_job_service.calls[0]["query"] == "What was decided?"
    assert fake_job_service.calls[0]["source_types"] == ("report", "note")
    assert fake_job_service.calls[0]["limit"] == 3


def test_assistant_conversation_api_returns_persisted_messages(client, monkeypatch) -> None:
    fake_service = _FakeAssistantChatService()
    monkeypatch.setattr(
        assistant_chat_routes,
        "get_assistant_chat_service",
        lambda: fake_service,
    )

    response = client.get("/api/v1/assistant/conversations/conversation-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"] == "conversation-1"
    assert payload["title"] == "Decision follow-up"
    assert [message["role"] for message in payload["messages"]] == ["user", "assistant"]
    assert payload["messages"][1]["status"] == "completed"
    assert payload["messages"][1]["sources"][0]["source_type"] == "note"
    assert payload["messages"][1]["metadata"]["job_id"] == "job-1"
    assert fake_service.calls[0]["get_conversation_messages"]["conversation_id"] == "conversation-1"


def test_assistant_chat_api가_답변과_근거를_반환한다(client, monkeypatch) -> None:
    fake_service = _FakeAssistantChatService()
    monkeypatch.setattr(
        assistant_chat_routes,
        "get_assistant_chat_service",
        lambda: fake_service,
    )
    monkeypatch.setattr(
        assistant_chat_routes,
        "get_assistant_response_job_service",
        lambda: None,
    )

    response = client.post(
        "/api/v1/assistant/chat",
        json={
            "query": "다음 할 일은?",
            "conversation_id": "conversation-1",
            "history": [{"role": "user", "content": "이전 질문"}],
            "source_types": ["report"],
            "session_id": "session-1",
            "limit": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "다음 할 일은?"
    assert payload["conversation_id"] == "conversation-1"
    assert payload["answer"].startswith("결정된 다음 할 일")
    assert payload["source_count"] == 1
    assert payload["sources"][0]["chunk_heading"] == "결정 사항"
    assert fake_service.calls[0]["source_types"] == ("report",)
    assert fake_service.calls[0]["session_id"] == "session-1"
    assert fake_service.calls[0]["conversation_id"] == "conversation-1"
    assert fake_service.calls[0]["conversation_history"] == (
        {"role": "user", "content": "이전 질문"},
    )
    assert fake_service.calls[0]["limit"] == 3


def test_assistant_chat_api는_빈_질문을_거절한다(client) -> None:
    response = client.post("/api/v1/assistant/chat", json={"query": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "질문을 입력해 주세요."
