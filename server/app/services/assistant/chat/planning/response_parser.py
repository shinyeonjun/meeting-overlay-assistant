"""Assistant query-plan response parser."""

from __future__ import annotations

import re

from server.app.services.analysis.llm.json_response import load_json_object_response
from server.app.services.assistant.chat.models import AssistantQueryPlan
from server.app.services.assistant.chat.planning.defaults import (
    DEFAULT_RETRIEVAL_SOURCES,
)


def parse_plan(
    *,
    query: str,
    response_text: str,
    requested_source_types: tuple[str, ...],
) -> AssistantQueryPlan:
    """Convert a planner JSON response into an AssistantQueryPlan."""

    payload = _load_json_object(response_text)
    if payload is None:
        return build_default_plan(
            query=query,
            requested_source_types=requested_source_types,
        )

    search_query = _clean_string(payload.get("search_query")) or query
    answer_focus = _clean_string(payload.get("answer_focus"))
    target_dates = _coerce_target_dates(payload.get("target_dates"))
    time_scope = _clean_string(payload.get("time_scope"))
    time_expression = _clean_string(payload.get("time_expression"))
    resolved_time_range = _clean_string(payload.get("resolved_time_range"))
    session_scope = _coerce_session_scope(payload.get("session_scope"), query=query)
    content_focuses = _coerce_content_focuses(payload.get("content_focuses"), query=query)
    requires_knowledge = _coerce_requires_knowledge(
        payload.get("requires_knowledge"),
        query=query,
        content_focuses=content_focuses,
    )
    needs_clarification = bool(payload.get("needs_clarification"))
    clarification_question = _clean_string(payload.get("clarification_question")) or None
    confidence = _coerce_confidence(payload.get("confidence"))

    return AssistantQueryPlan(
        query=query,
        search_query=search_query,
        answer_focus=answer_focus,
        retrieval_sources=DEFAULT_RETRIEVAL_SOURCES,
        target_dates=target_dates,
        time_scope=time_scope,
        time_expression=time_expression,
        resolved_time_range=resolved_time_range,
        session_scope=session_scope,
        content_focuses=content_focuses,
        requires_knowledge=requires_knowledge,
        preferred_source_types=requested_source_types,
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
        confidence=confidence,
    )


def _load_json_object(response_text: str) -> dict[str, object] | None:
    text = response_text.strip()
    if not text:
        return None
    try:
        return load_json_object_response(text)
    except (TypeError, ValueError):
        return None


def build_default_plan(
    *,
    query: str,
    requested_source_types: tuple[str, ...],
) -> AssistantQueryPlan:
    """Build the neutral retrieval plan used when the planner response is unavailable."""

    return AssistantQueryPlan(
        query=query,
        search_query=query,
        retrieval_sources=DEFAULT_RETRIEVAL_SOURCES,
        session_scope=_infer_session_scope(query),
        content_focuses=_infer_content_focuses(query),
        requires_knowledge=_infer_requires_knowledge(query),
        preferred_source_types=requested_source_types,
        confidence=0.2,
    )


def _clean_string(value: object) -> str:
    return str(value).strip() if isinstance(value, str) else ""


def _coerce_target_dates(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    dates: list[str] = []
    seen: set[str] = set()
    for item in value:
        date_text = str(item).strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_text):
            continue
        if date_text in seen:
            continue
        dates.append(date_text)
        seen.add(date_text)
    return tuple(dates)


def _coerce_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(max(confidence, 0.0), 1.0)


def _coerce_session_scope(value: object, *, query: str) -> str:
    allowed = {"", "latest", "previous", "recent_list", "date", "month", "title", "all"}
    scope = str(value).strip() if isinstance(value, str) else ""
    if scope in allowed:
        return scope or _infer_session_scope(query)
    return _infer_session_scope(query)


def _coerce_content_focuses(value: object, *, query: str) -> tuple[str, ...]:
    allowed = {
        "summary",
        "decision",
        "action_item",
        "risk",
        "question",
        "discussion",
        "transcript",
        "metadata",
    }
    focuses: list[str] = []
    seen: set[str] = set()
    if isinstance(value, list):
        for item in value:
            focus = str(item).strip()
            if focus in allowed and focus not in seen:
                focuses.append(focus)
                seen.add(focus)
    if focuses:
        return tuple(focuses)
    return _infer_content_focuses(query)


def _coerce_requires_knowledge(
    value: object,
    *,
    query: str,
    content_focuses: tuple[str, ...],
) -> bool:
    if isinstance(value, bool):
        if content_focuses and content_focuses != ("metadata",):
            return True
        return value and _infer_requires_knowledge(query)
    return True


def _infer_session_scope(query: str) -> str:
    text = re.sub(r"\s+", "", query.casefold())
    if re.search(r"\d{1,2}\s*[월/.-]", query) or re.search(r"\d{4}\s*[년/.-]", query):
        return "month"
    if any(term in text for term in ("가장최근", "최근회의", "지난회의", "마지막회의", "latest", "lastmeeting")):
        if any(term in text for term in ("목록", "리스트", "전부", "전체", "몇개", "몇개", "있었")):
            return "recent_list"
        return "latest"
    if any(term in text for term in ("몇개", "몇건", "목록", "리스트", "있었", "있어")):
        return "recent_list"
    return ""


def _infer_content_focuses(query: str) -> tuple[str, ...]:
    text = re.sub(r"\s+", "", query.casefold())
    focuses: list[str] = []
    checks = (
        ("decision", ("결정", "결정사항", "합의", "정한")),
        ("action_item", ("할일", "액션", "다음할일", "담당", "해야할")),
        ("risk", ("리스크", "위험", "이슈", "문제", "우려")),
        ("question", ("질문", "남은질문", "확인할")),
        ("summary", ("요약", "정리", "핵심")),
        ("transcript", ("원문", "발언", "누가말", "전사")),
        ("discussion", ("논의", "얘기", "이야기", "내용")),
    )
    for focus, terms in checks:
        if any(term in text for term in terms):
            focuses.append(focus)
    return tuple(focuses) or ("metadata",)


def _infer_requires_knowledge(query: str) -> bool:
    focuses = _infer_content_focuses(query)
    return focuses != ("metadata",)
