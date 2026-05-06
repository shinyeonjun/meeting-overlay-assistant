"""assistant chat 답변 모델."""

from __future__ import annotations

from dataclasses import dataclass

from server.app.domain.retrieval import RetrievalSearchResult


@dataclass(frozen=True)
class AssistantChatResult:
    """챗봇 답변과 답변에 사용한 근거."""

    query: str
    answer: str
    sources: list[RetrievalSearchResult]
