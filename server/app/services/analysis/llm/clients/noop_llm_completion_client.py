"""기본 no-op completion client."""

from __future__ import annotations

from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)


class NoOpLLMCompletionClient(LLMCompletionClient):
    """기본적으로 빈 JSON 결과를 돌려주는 completion client."""

    def complete(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        response_schema: dict[str, object] | None = None,
        keep_alive: str | None = None,
    ) -> str:
        """프롬프트를 무시하고 빈 후보 목록 JSON을 반환한다."""
        del prompt, system_prompt, response_schema, keep_alive
        return '{"candidates": []}'
