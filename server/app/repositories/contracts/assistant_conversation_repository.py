"""Assistant conversation repository contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from server.app.domain.models.assistant_conversation import (
    AssistantConversation,
    AssistantMessage,
)


class AssistantConversationRepository(ABC):
    """Persistence contract for assistant conversations and messages."""

    @abstractmethod
    def get_conversation(
        self,
        *,
        conversation_id: str,
        workspace_id: str,
    ) -> AssistantConversation | None:
        raise NotImplementedError

    @abstractmethod
    def list_conversations(
        self,
        *,
        workspace_id: str,
        user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int = 30,
    ) -> list[AssistantConversation]:
        raise NotImplementedError

    @abstractmethod
    def delete_conversation(
        self,
        *,
        conversation_id: str,
        workspace_id: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    def upsert_conversation(
        self,
        conversation: AssistantConversation,
    ) -> AssistantConversation:
        raise NotImplementedError

    @abstractmethod
    def list_messages(
        self,
        *,
        conversation_id: str,
        workspace_id: str,
        limit: int = 40,
        statuses: tuple[str, ...] = (),
    ) -> list[AssistantMessage]:
        raise NotImplementedError

    @abstractmethod
    def append_message(self, message: AssistantMessage) -> AssistantMessage:
        raise NotImplementedError

    @abstractmethod
    def update_message(
        self,
        *,
        message_id: str,
        content: str,
        status: str,
        error_message: str | None = None,
        sources_json: list[dict] | None = None,
        metadata_json: dict | None = None,
    ) -> AssistantMessage | None:
        raise NotImplementedError
