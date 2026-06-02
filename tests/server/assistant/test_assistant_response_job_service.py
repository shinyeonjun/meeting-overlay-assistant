"""assistant response job service tests."""

from dataclasses import replace

from server.app.domain.models.assistant_conversation import (
    AssistantConversation,
    AssistantMessage,
)
from server.app.domain.models.assistant_response_job import AssistantResponseJob
from server.app.domain.retrieval import RetrievalSearchResult
from server.app.services.assistant.chat.models import AssistantChatResult
from server.app.services.assistant.jobs import AssistantResponseJobService


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
        self.conversations[conversation.id] = conversation
        return conversation

    def list_messages(
        self,
        *,
        conversation_id: str,
        workspace_id: str,
        limit: int = 40,
        statuses: tuple[str, ...] = (),
    ):
        messages = [item for item in self.messages if item.conversation_id == conversation_id]
        if statuses:
            messages = [item for item in messages if item.status in statuses]
        return messages[-limit:]

    def append_message(self, message: AssistantMessage):
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


class _FakeJobRepository:
    def __init__(self):
        self.jobs = {}

    def save(self, job: AssistantResponseJob):
        self.jobs[job.id] = job
        return job

    def update(self, job: AssistantResponseJob):
        self.jobs[job.id] = job
        return job

    def get_by_id(self, job_id: str):
        return self.jobs.get(job_id)

    def list_pending(self, limit: int = 10):
        return [job for job in self.jobs.values() if job.status == "pending"][:limit]

    def claim_available(
        self,
        *,
        worker_id: str,
        lease_expires_at: str,
        claimed_at: str,
        limit: int = 10,
    ):
        claimed = []
        for job in self.list_pending(limit):
            updated = job.mark_processing(
                claimed_by_worker_id=worker_id,
                lease_expires_at=lease_expires_at,
                started_at=claimed_at,
            )
            self.jobs[job.id] = updated
            claimed.append(updated)
        return claimed

    def renew_lease(self, *, job_id: str, worker_id: str, lease_expires_at: str) -> bool:
        job = self.jobs.get(job_id)
        if job is None or job.claimed_by_worker_id != worker_id:
            return False
        self.jobs[job_id] = replace(job, lease_expires_at=lease_expires_at)
        return True


class _FakeChatService:
    def __init__(self):
        self.calls = []

    def generate_answer(self, **kwargs):
        self.calls.append(kwargs)
        return AssistantChatResult(
            query=kwargs["query"],
            answer="The proposal share was decided. [S1]",
            sources=[
                RetrievalSearchResult(
                    chunk_id="chunk-1",
                    document_id="doc-1",
                    source_type="report",
                    source_id="source-1",
                    document_title="Decision meeting",
                    chunk_text="The team decided to share the proposal by Friday.",
                    chunk_heading="Decision",
                    distance=0.1,
                )
            ],
            conversation_id=kwargs["conversation_id"],
        )


class _FailingQueue:
    def publish(self, job_id: str) -> bool:
        raise RuntimeError(f"queue unavailable: {job_id}")

    def wait_for_job(self, timeout_seconds: float) -> str | None:
        return None


def test_assistant_response_job_service_submits_and_processes_turn() -> None:
    conversation_repository = _FakeConversationRepository()
    job_repository = _FakeJobRepository()
    chat_service = _FakeChatService()
    service = AssistantResponseJobService(
        repository=job_repository,
        conversation_repository=conversation_repository,
        chat_service=chat_service,
    )

    submission = service.submit_question(
        workspace_id="workspace-1",
        user_id="user-1",
        query="What was decided?",
        source_types=("report", "note"),
        conversation_history=({"role": "user", "content": "Earlier question"},),
        limit=5,
        dispatch=False,
    )

    assert submission.job.status == "pending"
    assert submission.assistant_message.status == "pending"
    assert submission.job.request_json["conversation_history"] == [
        {"role": "user", "content": "Earlier question"}
    ]

    processed = service.process_job(submission.job.id)

    assert processed.status == "completed"
    messages = conversation_repository.list_messages(
        conversation_id=submission.conversation.id,
        workspace_id="workspace-1",
    )
    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[1].status == "completed"
    assert messages[1].content == "The proposal share was decided. [S1]"
    assert messages[1].sources_json[0]["chunk_id"] == "chunk-1"
    assert chat_service.calls[0]["source_types"] == ("report", "note")
    assert chat_service.calls[0]["limit"] == 5


def test_assistant_response_job_service_keeps_pending_job_when_queue_publish_fails() -> None:
    conversation_repository = _FakeConversationRepository()
    job_repository = _FakeJobRepository()
    service = AssistantResponseJobService(
        repository=job_repository,
        conversation_repository=conversation_repository,
        chat_service=_FakeChatService(),
        job_queue=_FailingQueue(),
    )

    submission = service.submit_question(
        workspace_id="workspace-1",
        user_id="user-1",
        query="What was decided?",
        dispatch=True,
    )

    assert submission.dispatched is False
    assert job_repository.get_by_id(submission.job.id).status == "pending"
    messages = conversation_repository.list_messages(
        conversation_id=submission.conversation.id,
        workspace_id="workspace-1",
    )
    assert messages[1].status == "pending"
