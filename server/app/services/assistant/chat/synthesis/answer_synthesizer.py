"""assistant 답변 합성기."""

from __future__ import annotations

import logging

from server.app.domain.retrieval import RetrievalSearchResult
from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.assistant.chat.models import (
    AssistantQueryPlan,
    AssistantTimeContext,
)
from server.app.services.assistant.chat.synthesis.fallback import build_fallback_answer
from server.app.services.assistant.chat.synthesis.prompt_builder import (
    build_system_prompt,
    build_user_prompt,
)
from server.app.services.assistant.chat.synthesis.response_parser import normalize_answer

logger = logging.getLogger(__name__)


class AssistantAnswerSynthesizer:
    """검색 근거를 바탕으로 최종 답변을 생성한다."""

    def __init__(self, *, completion_client: LLMCompletionClient) -> None:
        self._completion_client = completion_client

    def synthesize(
        self,
        *,
        plan: AssistantQueryPlan,
        sources: list[RetrievalSearchResult],
        time_context: AssistantTimeContext,
    ) -> str:
        """LLM 답변을 생성하고 실패 시 근거 기반 fallback을 반환한다."""

        try:
            response_text = self._completion_client.complete(
                build_user_prompt(
                    plan=plan,
                    sources=sources,
                    time_context=time_context,
                ),
                system_prompt=build_system_prompt(),
            )
            answer = normalize_answer(response_text)
        except Exception:
            logger.exception(
                "assistant LLM 답변 생성 실패: query_chars=%s",
                len(plan.query),
            )
            answer = ""
        return answer or build_fallback_answer(sources)
