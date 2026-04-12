"""세션 영역의 topic summarizer 서비스를 제공한다."""
from __future__ import annotations

from typing import Protocol

from server.app.services.sessions.topic_helpers import (
    LLMTopicSummarizer,
    NoOpTopicSummarizer,
    TopicHeuristicSummarizer,
)


class TopicSummarizer(Protocol):
    """현재 주제 요약기 인터페이스."""

    def summarize(
        self,
        session_id: str,
        topic_texts: list[str],
        fallback_topic: str | None = None,
    ) -> str | None:
        """최근 발화 묶음을 기반으로 현재 주제를 요약한다."""


__all__ = [
    "LLMTopicSummarizer",
    "NoOpTopicSummarizer",
    "TopicHeuristicSummarizer",
    "TopicSummarizer",
]
