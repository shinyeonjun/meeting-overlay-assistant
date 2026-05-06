"""assistant 요청 스키마."""

from pydantic import BaseModel


class AssistantChatRequest(BaseModel):
    """챗봇 질문 요청."""

    query: str
    source_types: list[str] | None = None
    session_id: str | None = None
    account_id: str | None = None
    contact_id: str | None = None
    context_thread_id: str | None = None
    limit: int = 8
