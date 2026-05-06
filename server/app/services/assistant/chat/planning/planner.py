"""LLM 기반 assistant 질문 계획기."""

from __future__ import annotations

import logging

from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.assistant.chat.models import (
    AssistantQueryPlan,
    AssistantTimeContext,
)
from server.app.services.assistant.chat.planning.prompt_builder import (
    build_planner_prompt,
    build_planner_system_prompt,
)
from server.app.services.assistant.chat.planning.response_parser import parse_plan
from server.app.services.assistant.chat.planning.schemas import QUERY_PLAN_RESPONSE_SCHEMA

logger = logging.getLogger(__name__)


class AssistantQueryPlanner:
    """사용자 질문을 RAG 검색 계획으로 바꾼다."""

    def __init__(
        self,
        *,
        completion_client: LLMCompletionClient,
    ) -> None:
        self._completion_client = completion_client

    def plan(
        self,
        *,
        query: str,
        time_context: AssistantTimeContext,
        requested_source_types: tuple[str, ...] = (),
    ) -> AssistantQueryPlan:
        """코드 고정 분류 없이 LLM JSON 결과로 검색 계획을 만든다."""

        normalized_query = query.strip()
        if not normalized_query:
            return AssistantQueryPlan(query=query, search_query="")

        requested = _normalize_source_types(requested_source_types)
        try:
            response_text = self._completion_client.complete(
                build_planner_prompt(
                    query=normalized_query,
                    requested_source_types=requested,
                    time_context_text=time_context.render_for_prompt(),
                ),
                system_prompt=build_planner_system_prompt(),
                response_schema=QUERY_PLAN_RESPONSE_SCHEMA,
            )
            return parse_plan(
                query=normalized_query,
                response_text=response_text,
                requested_source_types=requested,
            )
        except Exception:
            logger.exception(
                "assistant 질문 계획 생성 실패: query_chars=%s",
                len(normalized_query),
            )
            return AssistantQueryPlan(query=normalized_query, search_query=normalized_query)


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
