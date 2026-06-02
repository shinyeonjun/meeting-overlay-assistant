"""assistant 질문 계획 fast path."""

from __future__ import annotations

import re

from server.app.services.assistant.chat.models import AssistantQueryPlan
from server.app.services.assistant.chat.history_context import (
    build_contextual_search_query,
)

_DATE_PATTERN = re.compile(
    r"(\d{4}[-./년]\s*\d{1,2}[-./월]\s*\d{1,2}|\d{1,2}\s*월\s*\d{1,2}\s*일)"
)

_TIME_SCOPE_TERMS = (
    "오늘",
    "어제",
    "그제",
    "그저께",
    "최근",
    "이번주",
    "이번 주",
    "지난주",
    "지난 주",
    "저번주",
    "저번 주",
    "이번달",
    "이번 달",
    "지난달",
    "지난 달",
    "저번달",
    "저번 달",
)

_SESSION_LOOKUP_TERMS = (
    "회의 목록",
    "회의 리스트",
    "회의 뭐",
    "회의 뭐였",
    "어떤 회의",
    "무슨 회의",
    "몇 개",
    "몇개",
    "언제",
    "날짜",
    "시간",
    "세션",
    "session",
)


def build_fast_query_plan(
    *,
    query: str,
    requested_source_types: tuple[str, ...] = (),
    conversation_history=(),
) -> AssistantQueryPlan:
    """LLM planning 없이 지식 검색으로 바로 들어가는 기본 계획을 만든다."""

    normalized_query = query.strip()
    return AssistantQueryPlan(
        query=normalized_query,
        search_query=build_contextual_search_query(
            query=normalized_query,
            conversation_history=conversation_history,
        ),
        retrieval_sources=("knowledge",),
        preferred_source_types=_normalize_source_types(requested_source_types),
        confidence=0.65,
    )


def should_use_llm_planner(query: str) -> bool:
    """시간/세션 해석이 필요한 질문만 LLM planner로 보낸다."""

    normalized = " ".join(query.strip().split()).casefold()
    if not normalized:
        return False
    compact = normalized.replace(" ", "")
    if _DATE_PATTERN.search(normalized):
        return True
    if any(term.replace(" ", "") in compact for term in _TIME_SCOPE_TERMS):
        return True
    if any(term in normalized for term in _SESSION_LOOKUP_TERMS):
        return True
    return False


def _normalize_source_types(source_types: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for source_type in source_types:
        value = source_type.strip()
        if not value or value in seen:
            continue
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)
