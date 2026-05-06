"""assistant 질문 계획 응답 파서."""

from __future__ import annotations

import json
import re
from typing import Any

from server.app.services.assistant.chat.models import AssistantQueryPlan


def parse_plan(
    *,
    query: str,
    response_text: str,
    requested_source_types: tuple[str, ...],
) -> AssistantQueryPlan:
    """LLM JSON 응답을 AssistantQueryPlan으로 변환한다."""

    payload = _load_json_object(response_text)
    if payload is None:
        return AssistantQueryPlan(query=query, search_query=query)

    search_query = _clean_string(payload.get("search_query")) or query
    answer_focus = _clean_string(payload.get("answer_focus"))
    retrieval_sources = _coerce_retrieval_sources(payload.get("retrieval_sources"))
    target_dates = _coerce_target_dates(payload.get("target_dates"))
    time_scope = _clean_string(payload.get("time_scope"))
    time_expression = _clean_string(payload.get("time_expression"))
    resolved_time_range = _clean_string(payload.get("resolved_time_range"))
    needs_clarification = bool(payload.get("needs_clarification"))
    clarification_question = _clean_string(payload.get("clarification_question")) or None
    confidence = _coerce_confidence(payload.get("confidence"))

    return AssistantQueryPlan(
        query=query,
        search_query=search_query,
        answer_focus=answer_focus,
        retrieval_sources=retrieval_sources,
        target_dates=target_dates,
        time_scope=time_scope,
        time_expression=time_expression,
        resolved_time_range=resolved_time_range,
        preferred_source_types=requested_source_types,
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
        confidence=confidence,
    )


def _load_json_object(response_text: str) -> dict[str, Any] | None:
    text = response_text.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match is None:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _clean_string(value: object) -> str:
    return str(value).strip() if isinstance(value, str) else ""


def _coerce_retrieval_sources(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ("knowledge",)
    allowed = {"knowledge", "sessions"}
    sources: list[str] = []
    seen: set[str] = set()
    for item in value:
        source = str(item).strip()
        if source not in allowed or source in seen:
            continue
        sources.append(source)
        seen.add(source)
    return tuple(sources) or ("knowledge",)


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
