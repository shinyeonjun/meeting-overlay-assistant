from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.retrieval import RetrievalSearchResult
from server.app.infrastructure.persistence.postgresql.repositories import (
    PostgreSQLAssistantConversationRepository,
    PostgreSQLAssistantResponseJobRepository,
)
from server.app.services.assistant.chat.models import AssistantChatResult
from server.app.services.assistant.jobs import AssistantResponseJobService
from server.scripts.admin.manage_postgresql import ensure_assistant_chat_schema


class _FakeChatService:
    def __init__(self):
        self.calls = []

    def generate_answer(self, **kwargs):
        self.calls.append(kwargs)
        return AssistantChatResult(
            query=kwargs["query"],
            answer="Friday proposal sharing was confirmed. [S1]",
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


def test_assistant_response_job_roundtrip_with_postgresql_schema(isolated_database):
    ensure_assistant_chat_schema(database=isolated_database, execute=True)
    conversation_repository = PostgreSQLAssistantConversationRepository(isolated_database)
    job_repository = PostgreSQLAssistantResponseJobRepository(isolated_database)
    chat_service = _FakeChatService()
    service = AssistantResponseJobService(
        repository=job_repository,
        conversation_repository=conversation_repository,
        chat_service=chat_service,
    )

    submission = service.submit_question(
        workspace_id=DEFAULT_WORKSPACE_ID,
        query="What decision remains?",
        source_types=("note", "report"),
        session_id="session-1",
        limit=4,
        dispatch=False,
    )

    assert submission.job.status == "pending"
    claimed_jobs = service.claim_available_jobs(
        worker_id="worker-1",
        lease_duration_seconds=60,
        limit=1,
    )
    assert [job.id for job in claimed_jobs] == [submission.job.id]

    processed = service.process_job(
        claimed_jobs[0].id,
        expected_worker_id="worker-1",
    )

    assert processed.status == "completed"
    persisted_job = job_repository.get_by_id(submission.job.id)
    assert persisted_job is not None
    assert persisted_job.status == "completed"
    assert chat_service.calls[0]["workspace_id"] == DEFAULT_WORKSPACE_ID
    assert chat_service.calls[0]["source_types"] == ("note", "report")
    assert chat_service.calls[0]["limit"] == 4

    messages = conversation_repository.list_messages(
        conversation_id=submission.conversation.id,
        workspace_id=DEFAULT_WORKSPACE_ID,
    )
    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[0].content == "What decision remains?"
    assert messages[1].status == "completed"
    assert messages[1].content == "Friday proposal sharing was confirmed. [S1]"
    assert messages[1].sources_json[0]["source_type"] == "note"
    assert messages[1].metadata_json["job_id"] == submission.job.id
