"""LLM completion client 인터페이스."""

from __future__ import annotations

from typing import Protocol


class LLMCompletionClient(Protocol):
    """프롬프트를 보내고 문자열 응답을 받는 completion client 인터페이스."""

    def complete(self, prompt: str) -> str:
        """프롬프트를 실행하고 문자열 응답을 반환한다."""
