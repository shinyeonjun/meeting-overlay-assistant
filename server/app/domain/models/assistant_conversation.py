"""Assistant conversation persistence models."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from server.app.core.identifiers import generate_uuid_str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AssistantConversation:
    """A persisted chatbot conversation scoped to a workspace/context."""

    id: str
    workspace_id: str
    title: str
    status: str
    created_at: str
    updated_at: str
    user_id: str | None = None
    account_id: str | None = None
    contact_id: str | None = None
    context_thread_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        workspace_id: str,
        title: str,
        conversation_id: str | None = None,
        user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
    ) -> "AssistantConversation":
        now = _utc_now_iso()
        return cls(
            id=conversation_id or generate_uuid_str(),
            workspace_id=workspace_id,
            title=title,
            status="active",
            user_id=user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            created_at=now,
            updated_at=now,
        )

    def touch(self) -> "AssistantConversation":
        return replace(self, updated_at=_utc_now_iso())


@dataclass(frozen=True)
class AssistantMessage:
    """A single persisted chatbot message."""

    id: str
    conversation_id: str
    role: str
    content: str
    status: str
    created_at: str
    updated_at: str
    error_message: str | None = None
    sources_json: list[dict] | None = None
    metadata_json: dict | None = None

    @classmethod
    def create(
        cls,
        *,
        conversation_id: str,
        role: str,
        content: str,
        status: str = "completed",
        error_message: str | None = None,
        sources_json: list[dict] | None = None,
        metadata_json: dict | None = None,
    ) -> "AssistantMessage":
        now = _utc_now_iso()
        return cls(
            id=generate_uuid_str(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            status=status,
            error_message=error_message,
            sources_json=sources_json or [],
            metadata_json=metadata_json or {},
            created_at=now,
            updated_at=now,
        )
