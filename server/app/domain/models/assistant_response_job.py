"""Assistant response generation job model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from server.app.core.identifiers import generate_uuid_str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_after_seconds_iso(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=max(seconds, 1))).isoformat()


@dataclass(frozen=True)
class AssistantResponseJob:
    """Background job that generates one assistant response message."""

    id: str
    conversation_id: str
    user_message_id: str
    assistant_message_id: str
    workspace_id: str
    status: str
    query: str
    request_json: dict
    error_message: str | None
    requested_by_user_id: str | None
    claimed_by_worker_id: str | None
    lease_expires_at: str | None
    attempt_count: int
    created_at: str
    started_at: str | None
    completed_at: str | None

    @classmethod
    def create_pending(
        cls,
        *,
        conversation_id: str,
        user_message_id: str,
        assistant_message_id: str,
        workspace_id: str,
        query: str,
        request_json: dict,
        requested_by_user_id: str | None = None,
    ) -> "AssistantResponseJob":
        return cls(
            id=generate_uuid_str(),
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            workspace_id=workspace_id,
            status="pending",
            query=query,
            request_json=request_json,
            error_message=None,
            requested_by_user_id=requested_by_user_id,
            claimed_by_worker_id=None,
            lease_expires_at=None,
            attempt_count=0,
            created_at=_utc_now_iso(),
            started_at=None,
            completed_at=None,
        )

    def mark_processing(
        self,
        *,
        claimed_by_worker_id: str | None = None,
        lease_expires_at: str | None = None,
        started_at: str | None = None,
    ) -> "AssistantResponseJob":
        return AssistantResponseJob(
            id=self.id,
            conversation_id=self.conversation_id,
            user_message_id=self.user_message_id,
            assistant_message_id=self.assistant_message_id,
            workspace_id=self.workspace_id,
            status="processing",
            query=self.query,
            request_json=self.request_json,
            error_message=None,
            requested_by_user_id=self.requested_by_user_id,
            claimed_by_worker_id=claimed_by_worker_id,
            lease_expires_at=lease_expires_at,
            attempt_count=self.attempt_count + 1,
            created_at=self.created_at,
            started_at=started_at or _utc_now_iso(),
            completed_at=None,
        )

    def mark_completed(self) -> "AssistantResponseJob":
        return AssistantResponseJob(
            id=self.id,
            conversation_id=self.conversation_id,
            user_message_id=self.user_message_id,
            assistant_message_id=self.assistant_message_id,
            workspace_id=self.workspace_id,
            status="completed",
            query=self.query,
            request_json=self.request_json,
            error_message=None,
            requested_by_user_id=self.requested_by_user_id,
            claimed_by_worker_id=None,
            lease_expires_at=None,
            attempt_count=self.attempt_count,
            created_at=self.created_at,
            started_at=self.started_at or _utc_now_iso(),
            completed_at=_utc_now_iso(),
        )

    def mark_failed(self, error_message: str) -> "AssistantResponseJob":
        return AssistantResponseJob(
            id=self.id,
            conversation_id=self.conversation_id,
            user_message_id=self.user_message_id,
            assistant_message_id=self.assistant_message_id,
            workspace_id=self.workspace_id,
            status="failed",
            query=self.query,
            request_json=self.request_json,
            error_message=error_message,
            requested_by_user_id=self.requested_by_user_id,
            claimed_by_worker_id=None,
            lease_expires_at=None,
            attempt_count=self.attempt_count,
            created_at=self.created_at,
            started_at=self.started_at or _utc_now_iso(),
            completed_at=_utc_now_iso(),
        )

    def with_lease(self, *, worker_id: str, lease_seconds: int) -> "AssistantResponseJob":
        return self.mark_processing(
            claimed_by_worker_id=worker_id,
            lease_expires_at=_utc_after_seconds_iso(lease_seconds),
        )
