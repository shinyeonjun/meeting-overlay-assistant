from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.retrieval import RetrievalSearchResult
from server.app.infrastructure.persistence.postgresql.repositories import (
    PostgreSQLAssistantConversationRepository,
    PostgreSQLAssistantResponseJobRepository,
)
from server.app.services.assistant.chat.models import AssistantChatResult
from server.app.services.assistant.jobs import AssistantResponseJobService
from server.app.workers import assistant_response_worker
from server.app.api.http.routes.assistant import chat as assistant_chat_routes
from server.scripts.admin.manage_postgresql import ensure_assistant_chat_schema


class _FakeAsyncChatService:
    def __init__(self):
        self.calls = []

    def generate_answer(self, **kwargs):
        self.calls.append(kwargs)
        return AssistantChatResult(
            query=kwargs["query"],
            answer="The proposal will be shared by Friday. [S1]",
            sources=[
                RetrievalSearchResult(
                    chunk_id="chunk-1",
                    document_id="document-1",
                    source_type="note",
                    source_id="session-1",
                    document_title="7 minute test meeting",
                    chunk_text="The proposal should be shared by Friday.",
                    chunk_heading="Decision",
                    distance=0.08,
                    session_id="session-1",
                )
            ],
            conversation_id=kwargs["conversation_id"],
        )


class _ConversationReaderService:
    def __init__(self, repository):
        self._repository = repository

    def get_conversation_messages(
        self,
        *,
        workspace_id: str,
        conversation_id: str,
        limit: int = 80,
    ):
        conversation = self._repository.get_conversation(
            conversation_id=conversation_id,
            workspace_id=workspace_id,
        )
        if conversation is None:
            return None
        return conversation, self._repository.list_messages(
            conversation_id=conversation_id,
            workspace_id=workspace_id,
            limit=limit,
        )


def test_assistant_api_roundtrip_persists_job_and_restores_worker_answer(
    client,
    isolated_database,
    monkeypatch,
):
    ensure_assistant_chat_schema(database=isolated_database, execute=True)
    conversation_repository = PostgreSQLAssistantConversationRepository(isolated_database)
    job_repository = PostgreSQLAssistantResponseJobRepository(isolated_database)
    fake_chat_service = _FakeAsyncChatService()
    job_service = AssistantResponseJobService(
        repository=job_repository,
        conversation_repository=conversation_repository,
        chat_service=fake_chat_service,
    )
    reader_service = _ConversationReaderService(conversation_repository)
    monkeypatch.setattr(
        assistant_chat_routes,
        "get_assistant_chat_service",
        lambda: reader_service,
    )
    monkeypatch.setattr(
        assistant_chat_routes,
        "get_assistant_response_job_service",
        lambda: job_service,
    )
    monkeypatch.setattr(
        assistant_response_worker,
        "get_assistant_response_job_service",
        lambda: job_service,
    )

    response = client.post(
        "/api/v1/assistant/chat",
        json={
            "query": "What was decided?",
            "source_types": ["note", "report"],
            "session_id": "session-1",
            "limit": 2,
        },
    )

    assert response.status_code == 200
    pending_payload = response.json()
    assert pending_payload["status"] == "pending"
    assert pending_payload["conversation_id"]
    assert pending_payload["job_id"]
    assert pending_payload["message_id"]

    processed_count = assistant_response_worker.run_once(
        worker_id="assistant-worker-test",
        batch_size=1,
        lease_seconds=60,
    )

    assert processed_count == 1
    assert fake_chat_service.calls[0]["workspace_id"] == DEFAULT_WORKSPACE_ID
    assert fake_chat_service.calls[0]["source_types"] == ("note", "report")
    assert fake_chat_service.calls[0]["limit"] == 2

    restored_response = client.get(
        f"/api/v1/assistant/conversations/{pending_payload['conversation_id']}",
    )

    assert restored_response.status_code == 200
    restored_payload = restored_response.json()
    assert restored_payload["conversation_id"] == pending_payload["conversation_id"]
    assert [message["role"] for message in restored_payload["messages"]] == [
        "user",
        "assistant",
    ]
    assert restored_payload["messages"][0]["content"] == "What was decided?"
    assert restored_payload["messages"][1]["status"] == "completed"
    assert restored_payload["messages"][1]["content"] == (
        "The proposal will be shared by Friday. [S1]"
    )
    assert restored_payload["messages"][1]["sources"][0]["source_type"] == "note"
    assert restored_payload["messages"][1]["metadata"]["job_id"] == pending_payload["job_id"]
