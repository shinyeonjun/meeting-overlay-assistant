"""assistant 요청 스키마."""

from pydantic import BaseModel


class AssistantChatHistoryItemRequest(BaseModel):
    """챗봇 후속 질문용 최근 대화 항목."""

    role: str
    content: str


class AssistantChatRequest(BaseModel):
    """챗봇 질문 요청."""

    query: str
    conversation_id: str | None = None
    history: list[AssistantChatHistoryItemRequest] | None = None
    source_types: list[str] | None = None
    session_id: str | None = None
    account_id: str | None = None
    contact_id: str | None = None
    context_thread_id: str | None = None
    limit: int = 8
