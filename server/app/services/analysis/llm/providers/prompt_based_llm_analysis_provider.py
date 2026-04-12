"""프롬프트/파서 기반 LLM provider."""

from __future__ import annotations

import logging

from server.app.services.analysis.llm.clients.noop_llm_completion_client import (
    NoOpLLMCompletionClient,
)
from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.analysis.llm.contracts.llm_models import (
    LLMAnalysisInput,
    LLMAnalysisResult,
)
from server.app.services.analysis.llm.contracts.llm_provider import LLMAnalysisProvider
from server.app.services.analysis.llm.extraction.llm_prompt_builder import (
    LLMAnalysisPromptBuilder,
)
from server.app.services.analysis.llm.extraction.llm_response_parser import (
    LLMAnalysisResponseParser,
)
from server.app.services.analysis.observability import (
    record_insight_candidates_emitted,
    record_insight_provider_exception,
    record_insight_provider_invocation,
)


logger = logging.getLogger(__name__)


class PromptBasedLLMAnalysisProvider(LLMAnalysisProvider):
    """프롬프트 생성과 JSON 파싱을 조합하는 기본 LLM provider."""

    def __init__(
        self,
        completion_client: LLMCompletionClient | None = None,
        prompt_builder: LLMAnalysisPromptBuilder | None = None,
        response_parser: LLMAnalysisResponseParser | None = None,
        backend_name: str = "unknown",
    ) -> None:
        self._completion_client = completion_client or NoOpLLMCompletionClient()
        self._prompt_builder = prompt_builder or LLMAnalysisPromptBuilder()
        self._response_parser = response_parser or LLMAnalysisResponseParser()
        self._backend_name = backend_name

    def analyze(self, analysis_input: LLMAnalysisInput) -> LLMAnalysisResult:
        """프롬프트 생성 -> 문자열 응답 -> JSON 파싱 순서로 분석한다."""
        record_insight_provider_invocation(self._backend_name)
        try:
            prompt = self._prompt_builder.build(analysis_input)
            response_text = self._completion_client.complete(prompt)
        except Exception as error:
            logger.warning(
                "LLM 인사이트 호출 실패: backend=%s session_id=%s utterance_id=%s error=%s",
                self._backend_name,
                analysis_input.session_id,
                analysis_input.utterance_id,
                type(error).__name__,
            )
            record_insight_provider_exception(self._backend_name, type(error).__name__)
            return LLMAnalysisResult()

        result = self._response_parser.parse(response_text)
        record_insight_candidates_emitted(len(result.candidates))
        return result
