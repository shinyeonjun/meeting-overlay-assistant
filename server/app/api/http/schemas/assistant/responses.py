"""assistant 응답 스키마."""

from pydantic import BaseModel, Field

from server.app.api.http.schemas.retrieval import RetrievalSearchItemResponse


class AssistantChatResponse(BaseModel):
    """챗봇 답변 응답."""

    query: str
    conversation_id: str | None = None
    answer: str
    source_count: int
    sources: list[RetrievalSearchItemResponse]
    status: str = "completed"
    message_id: str | None = None
    job_id: str | None = None
    error_message: str | None = None


class AssistantConversationMessageResponse(BaseModel):
    """저장된 assistant 대화 메시지."""

    id: str
    role: str
    content: str
    status: str
    error_message: str | None = None
    sources: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    created_at: str
    updated_at: str


class AssistantConversationResponse(BaseModel):
    """저장된 assistant 대화 조회 응답."""

    conversation_id: str
    title: str
    status: str
    messages: list[AssistantConversationMessageResponse]


class AssistantConversationListItemResponse(BaseModel):
    """Assistant conversation list item."""

    conversation_id: str
    title: str
    status: str
    created_at: str
    updated_at: str


class AssistantConversationListResponse(BaseModel):
    """Assistant conversation list response."""

    conversations: list[AssistantConversationListItemResponse]
