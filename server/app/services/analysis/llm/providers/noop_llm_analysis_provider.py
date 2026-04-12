"""공통 영역의 noop llm analysis provider 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.analysis.llm.contracts.llm_models import (
    LLMAnalysisInput,
    LLMAnalysisResult,
)
from server.app.services.analysis.llm.contracts.llm_provider import LLMAnalysisProvider


class NoOpLLMAnalysisProvider(LLMAnalysisProvider):
    """아직 실제 LLM 연결이 없을 때 빈 결과를 반환하는 provider."""

    def analyze(self, analysis_input: LLMAnalysisInput) -> LLMAnalysisResult:
        """현재는 빈 후보 목록을 반환한다."""
        del analysis_input
        return LLMAnalysisResult()
