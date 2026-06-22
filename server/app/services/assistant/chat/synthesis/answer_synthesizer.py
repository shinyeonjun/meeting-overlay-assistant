"""Assistant answer synthesizer."""

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
from server.app.services.assistant.chat.synthesis.prompt_builder import (
    build_system_prompt,
    build_user_prompt,
)
from server.app.services.assistant.chat.synthesis.response_parser import normalize_answer

logger = logging.getLogger(__name__)


ANSWER_GENERATION_FAILED_MESSAGE = (
    "답변 생성에 실패했습니다. 근거를 임의로 요약하지 않고 다시 시도해 주세요."
)
EMPTY_ANSWER_MESSAGE = (
    "답변 생성 결과가 비어 있습니다. 근거를 임의로 요약하지 않고 다시 시도해 주세요."
)


class AssistantAnswerSynthesizer:
    """Generate the final answer from retrieved evidence."""

    def __init__(self, *, completion_client: LLMCompletionClient) -> None:
        self._completion_client = completion_client

    def synthesize(
        self,
        *,
        plan: AssistantQueryPlan,
        sources: list[RetrievalSearchResult],
        time_context: AssistantTimeContext,
        conversation_history=(),
    ) -> str:
        """Generate the final answer without substituting retrieved snippets as an answer."""

        try:
            response_text = self._completion_client.complete(
                build_user_prompt(
                    plan=plan,
                    sources=sources,
                    time_context=time_context,
                    conversation_history=conversation_history,
                ),
                system_prompt=build_system_prompt(),
            )
            answer = normalize_answer(response_text)
        except Exception:
            logger.exception(
                "assistant answer generation failed: query_chars=%s",
                len(plan.query),
            )
            return ANSWER_GENERATION_FAILED_MESSAGE
        if not answer:
            return EMPTY_ANSWER_MESSAGE
        return answer
