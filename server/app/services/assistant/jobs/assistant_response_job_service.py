"""Assistant response job service."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from uuid import UUID

from server.app.domain.models.assistant_conversation import (
    AssistantConversation,
    AssistantMessage,
)
from server.app.domain.models.assistant_response_job import AssistantResponseJob
from server.app.repositories.contracts.assistant_conversation_repository import (
    AssistantConversationRepository,
)
from server.app.repositories.contracts.assistant_response_job_repository import (
    AssistantResponseJobRepository,
)
from server.app.services.assistant.chat.history_context import (
    normalize_conversation_history,
)
from server.app.services.assistant.chat.service import AssistantChatService
from server.app.services.assistant.jobs.assistant_response_job_queue import (
    AssistantResponseJobQueue,
)
from server.app.services.reports.jobs.helpers.time_utils import (
    utc_after_seconds_iso,
    utc_now_iso,
)


logger = logging.getLogger(__name__)


class AssistantResponseJobStorageUnavailable(RuntimeError):
    """Raised when assistant job storage tables are not available yet."""


@dataclass(frozen=True)
class AssistantResponseJobSubmission:
    conversation: AssistantConversation
    user_message: AssistantMessage
    assistant_message: AssistantMessage
    job: AssistantResponseJob
    dispatched: bool


class AssistantResponseJobService:
    """Create and process background assistant response jobs."""

    def __init__(
        self,
        *,
        repository: AssistantResponseJobRepository,
        conversation_repository: AssistantConversationRepository,
        chat_service: AssistantChatService,
        job_queue: AssistantResponseJobQueue | None = None,
    ) -> None:
        self._repository = repository
        self._conversation_repository = conversation_repository
        self._chat_service = chat_service
        self._job_queue = job_queue

    @property
    def has_queue(self) -> bool:
        return self._job_queue is not None

    def submit_question(
        self,
        *,
        workspace_id: str,
        query: str,
        source_types: tuple[str, ...] = (),
        session_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        conversation_id: str | None = None,
        conversation_history=(),
        user_id: str | None = None,
        limit: int | None = None,
        dispatch: bool = True,
    ) -> AssistantResponseJobSubmission:
        """Persist a user turn and enqueue assistant response generation."""

        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("질문을 입력해 주세요.")

        try:
            conversation = AssistantConversation.create(
                conversation_id=_normalize_uuid_or_none(conversation_id),
                workspace_id=workspace_id,
                user_id=user_id,
                account_id=account_id,
                contact_id=contact_id,
                context_thread_id=context_thread_id,
                title=_build_conversation_title(normalized_query),
            )
            conversation = self._conversation_repository.upsert_conversation(conversation)
            stored_messages = self._conversation_repository.list_messages(
                conversation_id=conversation.id,
                workspace_id=workspace_id,
                limit=12,
                statuses=("completed",),
            )
            stored_history = tuple(
                {"role": message.role, "content": message.content}
                for message in stored_messages
                if message.role in {"user", "assistant"} and message.content
            )
            normalized_history = normalize_conversation_history(
                stored_history or conversation_history
            )

            user_message = self._conversation_repository.append_message(
                AssistantMessage.create(
                    conversation_id=conversation.id,
                    role="user",
                    content=normalized_query,
                )
            )
            assistant_message = self._conversation_repository.append_message(
                AssistantMessage.create(
                    conversation_id=conversation.id,
                    role="assistant",
                    content="",
                    status="pending",
                )
            )
            job = AssistantResponseJob.create_pending(
                conversation_id=conversation.id,
                user_message_id=user_message.id,
                assistant_message_id=assistant_message.id,
                workspace_id=workspace_id,
                query=normalized_query,
                requested_by_user_id=user_id,
                request_json={
                    "source_types": list(source_types),
                    "session_id": session_id,
                    "account_id": account_id,
                    "contact_id": contact_id,
                    "context_thread_id": context_thread_id,
                    "conversation_history": list(normalized_history),
                    "limit": limit,
                },
            )
            job = self._repository.save(job)
            assistant_message = self._conversation_repository.update_message(
                message_id=assistant_message.id,
                content="",
                status="pending",
                sources_json=[],
                metadata_json={"job_id": job.id, "query": normalized_query},
            ) or assistant_message
        except Exception as exc:
            raise AssistantResponseJobStorageUnavailable(
                "assistant response job storage is unavailable"
            ) from exc

        dispatched = False
        if dispatch:
            try:
                dispatched = self.dispatch_job(job.id)
            except Exception:
                logger.warning(
                    "assistant response job dispatch failed; DB fallback sweep can recover it: job_id=%s",
                    job.id,
                    exc_info=True,
                )
        return AssistantResponseJobSubmission(
            conversation=conversation,
            user_message=user_message,
            assistant_message=assistant_message,
            job=job,
            dispatched=dispatched,
        )

    def dispatch_job(self, job_id: str) -> bool:
        if self._job_queue is None:
            return False
        return self._job_queue.publish(job_id)

    def wait_for_dispatched_job(self, timeout_seconds: float) -> str | None:
        if self._job_queue is None:
            return None
        return self._job_queue.wait_for_job(timeout_seconds)

    def renew_job_lease(
        self,
        *,
        job_id: str,
        worker_id: str,
        lease_duration_seconds: int,
    ) -> bool:
        return self._repository.renew_lease(
            job_id=job_id,
            worker_id=worker_id,
            lease_expires_at=utc_after_seconds_iso(lease_duration_seconds),
        )

    def claim_available_jobs(
        self,
        *,
        worker_id: str,
        lease_duration_seconds: int,
        limit: int = 10,
    ) -> list[AssistantResponseJob]:
        return self._repository.claim_available(
            worker_id=worker_id,
            lease_expires_at=utc_after_seconds_iso(lease_duration_seconds),
            claimed_at=utc_now_iso(),
            limit=limit,
        )

    def process_job(
        self,
        job_id: str,
        *,
        expected_worker_id: str | None = None,
    ) -> AssistantResponseJob:
        job = self._resolve_processing_job(
            job_id=job_id,
            expected_worker_id=expected_worker_id,
        )
        if job.status == "completed":
            return job
        if job.status == "failed":
            return job

        request = job.request_json
        try:
            result = self._chat_service.generate_answer(
                workspace_id=job.workspace_id,
                query=job.query,
                source_types=tuple(_list_of_strings(request.get("source_types"))),
                session_id=_optional_string(request.get("session_id")),
                account_id=_optional_string(request.get("account_id")),
                contact_id=_optional_string(request.get("contact_id")),
                context_thread_id=_optional_string(request.get("context_thread_id")),
                conversation_id=job.conversation_id,
                conversation_history=request.get("conversation_history") or (),
                limit=_optional_int(request.get("limit")),
            )
            self._conversation_repository.update_message(
                message_id=job.assistant_message_id,
                content=result.answer,
                status="completed",
                sources_json=[asdict(source) for source in result.sources],
                metadata_json={
                    "job_id": job.id,
                    "query": result.query,
                    "source_count": len(result.sources),
                },
            )
            return self._repository.update(job.mark_completed())
        except Exception as exc:
            logger.exception(
                "assistant response job failed: job_id=%s conversation_id=%s worker_id=%s",
                job.id,
                job.conversation_id,
                expected_worker_id,
            )
            self._conversation_repository.update_message(
                message_id=job.assistant_message_id,
                content="",
                status="error",
                error_message=str(exc)[:1000],
                sources_json=[],
                metadata_json={"job_id": job.id, "query": job.query},
            )
            return self._repository.update(job.mark_failed(str(exc)[:1000]))

    def process_available_jobs(
        self,
        *,
        worker_id: str,
        lease_duration_seconds: int,
        limit: int = 10,
    ) -> list[AssistantResponseJob]:
        claimed_jobs = self.claim_available_jobs(
            worker_id=worker_id,
            lease_duration_seconds=lease_duration_seconds,
            limit=limit,
        )
        return [
            self.process_job(job.id, expected_worker_id=worker_id)
            for job in claimed_jobs
        ]

    def _resolve_processing_job(
        self,
        *,
        job_id: str,
        expected_worker_id: str | None,
    ) -> AssistantResponseJob:
        job = self._repository.get_by_id(job_id)
        if job is None:
            raise ValueError(f"assistant response job을 찾을 수 없습니다: {job_id}")
        if job.status in {"completed", "failed"}:
            return job

        if expected_worker_id is not None:
            if job.status != "processing":
                raise ValueError(f"claim되지 않은 assistant response job입니다: {job_id}")
            if job.claimed_by_worker_id != expected_worker_id:
                raise ValueError(f"다른 worker가 claim한 assistant response job입니다: {job_id}")
            return job

        if job.status == "processing":
            return job

        return self._repository.update(
            job.mark_processing(started_at=utc_now_iso())
        )


def _normalize_uuid_or_none(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(UUID(str(value).strip()))
    except ValueError:
        return None


def _build_conversation_title(query: str) -> str:
    normalized = " ".join(query.split())
    if not normalized:
        return "Assistant conversation"
    if len(normalized) <= 80:
        return normalized
    return normalized[:79].rstrip() + "..."


def _optional_string(value) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _list_of_strings(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
