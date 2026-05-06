"""assistant 응답 스키마."""

from pydantic import BaseModel

from server.app.api.http.schemas.retrieval import RetrievalSearchItemResponse


class AssistantChatResponse(BaseModel):
    """챗봇 답변 응답."""

    query: str
    answer: str
    source_count: int
    sources: list[RetrievalSearchItemResponse]
