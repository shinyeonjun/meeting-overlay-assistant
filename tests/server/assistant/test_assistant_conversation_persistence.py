"""assistant conversation persistence tests."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from server.app.domain.models.assistant_conversation import AssistantConversation
from server.app.domain.retrieval import RetrievalSearchResult
from server.app.services.assistant import AssistantChatService, AssistantTimeContext


def _fixed_time_context() -> AssistantTimeContext:
    return AssistantTimeContext(
        now=datetime(2026, 4, 30, 6, 0, 0, tzinfo=timezone(timedelta(hours=9))),
        timezone_name="Asia/Seoul",
    )


class _FakeRetrievalQueryService:
    def __init__(self, results):
        self.results = results

    def search(self, **kwargs):
        return self.results


class _FakeCompletionClient:
    def __init__(self, response):
        self.response = response

    def complete(self, prompt, *, system_prompt=None, response_schema=None, keep_alive=None):
        return self.response


class _FakeConversationRepository:
    def __init__(self):
        self.conversations = {}
        self.messages = []

    def get_conversation(self, *, conversation_id: str, workspace_id: str):
        conversation = self.conversations.get(conversation_id)
        if conversation is None or conversation.workspace_id != workspace_id:
            return None
        return conversation

    def upsert_conversation(self, conversation: AssistantConversation):
        existing = self.conversations.get(conversation.id)
        self.conversations[conversation.id] = replace(
            conversation,
            created_at=existing.created_at if existing is not None else conversation.created_at,
        )
        return self.conversations[conversation.id]

    def list_messages(
        self,
        *,
        conversation_id: str,
        workspace_id: str,
        limit: int = 40,
        statuses: tuple[str, ...] = (),
    ):
        conversation = self.get_conversation(
            conversation_id=conversation_id,
            workspace_id=workspace_id,
        )
        if conversation is None:
            return []
        messages = [item for item in self.messages if item.conversation_id == conversation_id]
        if statuses:
            messages = [item for item in messages if item.status in statuses]
        return messages[-limit:]

    def append_message(self, message):
        self.messages.append(message)
        return message

    def update_message(
        self,
        *,
        message_id: str,
        content: str,
        status: str,
        error_message: str | None = None,
        sources_json: list[dict] | None = None,
        metadata_json: dict | None = None,
    ):
        for index, message in enumerate(self.messages):
            if message.id != message_id:
                continue
            updated = replace(
                message,
                content=content,
                status=status,
                error_message=error_message,
                sources_json=sources_json or [],
                metadata_json=metadata_json or {},
            )
            self.messages[index] = updated
            return updated
        return None


def _result() -> RetrievalSearchResult:
    return RetrievalSearchResult(
        chunk_id="chunk-1",
        document_id="doc-1",
        source_type="report",
        source_id="source-1",
        document_title="Decision meeting",
        chunk_text="The team decided to share the proposal by Friday.",
        chunk_heading="Decision",
        distance=0.1,
    )


def test_assistant_chat_service_persists_conversation_turn() -> None:
    repository = _FakeConversationRepository()
    service = AssistantChatService(
        retrieval_query_service=_FakeRetrievalQueryService([_result()]),
        completion_client=_FakeCompletionClient("The proposal share was decided. [S1]"),
        time_context_factory=_fixed_time_context,
        assistant_conversation_repository=repository,
    )

    result = service.answer(
        workspace_id="workspace-1",
        user_id="user-1",
        query="What was decided?",
    )

    assert result.conversation_id in repository.conversations
    conversation = repository.conversations[result.conversation_id]
    assert conversation.workspace_id == "workspace-1"
    assert conversation.user_id == "user-1"
    messages = repository.list_messages(
        conversation_id=result.conversation_id,
        workspace_id="workspace-1",
    )
    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[0].content == "What was decided?"
    assert messages[1].status == "completed"
    assert messages[1].content == "The proposal share was decided. [S1]"
    assert messages[1].sources_json[0]["chunk_id"] == "chunk-1"
