"""assistant 질문 계획 모델."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssistantQueryPlan:
    """RAG 검색과 답변 합성을 위한 LLM 기반 질문 계획."""

    query: str
    search_query: str
    answer_focus: str = ""
    retrieval_sources: tuple[str, ...] = ("knowledge",)
    target_dates: tuple[str, ...] = ()
    time_scope: str = ""
    time_expression: str = ""
    resolved_time_range: str = ""
    preferred_source_types: tuple[str, ...] = ()
    needs_clarification: bool = False
    clarification_question: str | None = None
    confidence: float = 0.0
