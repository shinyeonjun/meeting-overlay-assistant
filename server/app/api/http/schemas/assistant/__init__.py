"""assistant 스키마 패키지 진입점."""

from server.app.api.http.schemas.assistant.requests import AssistantChatRequest
from server.app.api.http.schemas.assistant.responses import AssistantChatResponse

__all__ = [
    "AssistantChatRequest",
    "AssistantChatResponse",
]
