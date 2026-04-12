"""공통 영역의 llm completion client 서비스를 제공한다."""
from __future__ import annotations

from typing import Any, Protocol


class LLMCompletionClient(Protocol):
    """프롬프트를 보내고 문자열 응답을 받는 completion client 인터페이스."""

    def complete(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        response_schema: dict[str, Any] | None = None,
        keep_alive: str | None = None,
    ) -> str:
        """프롬프트를 실행하고 문자열 응답을 반환한다."""
