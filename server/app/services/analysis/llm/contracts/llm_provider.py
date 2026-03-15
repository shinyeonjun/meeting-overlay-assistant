"""LLM 분석 provider 인터페이스."""

from __future__ import annotations

from typing import Protocol

from server.app.services.analysis.llm.contracts.llm_models import (
    LLMAnalysisInput,
    LLMAnalysisResult,
)


class LLMAnalysisProvider(Protocol):
    """LLM 입력을 받아 이벤트 후보를 반환하는 provider 인터페이스."""

    def analyze(self, analysis_input: LLMAnalysisInput) -> LLMAnalysisResult:
        """입력을 분석해 구조화 후보를 반환한다."""
