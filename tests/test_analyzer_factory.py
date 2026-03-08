"""분석기 팩토리 테스트."""

import pytest

from backend.app.services.analysis.analyzers.analyzer_factory import create_meeting_analyzer
from backend.app.services.analysis.analyzers.fallback_meeting_analyzer import (
    FallbackMeetingAnalyzer,
)
from backend.app.services.analysis.analyzers.insight_pipeline_meeting_analyzer import (
    InsightPipelineMeetingAnalyzer,
)
from backend.app.services.analysis.analyzers.llm_based_meeting_analyzer import (
    LLMBasedMeetingAnalyzer,
)
from backend.app.services.analysis.analyzers.rule_based_meeting_analyzer import (
    RuleBasedMeetingAnalyzer,
)


class TestAnalyzerFactory:
    """설정 기반 분석기 생성 테스트."""

    def test_rule_based_설정이면_규칙기반_분석기를_반환한다(self):
        analyzer = create_meeting_analyzer("rule_based")

        assert isinstance(analyzer, RuleBasedMeetingAnalyzer)

    def test_llm_설정이면_llm_분석기를_반환한다(self):
        analyzer = create_meeting_analyzer("llm")

        assert isinstance(analyzer, LLMBasedMeetingAnalyzer)

    def test_hybrid_설정이면_fallback_분석기를_반환한다(self):
        analyzer = create_meeting_analyzer("hybrid")

        assert isinstance(analyzer, FallbackMeetingAnalyzer)

    def test_insight_pipeline_설정이면_조합형_분석기를_반환한다(self):
        analyzer = create_meeting_analyzer("insight_pipeline")

        assert isinstance(analyzer, InsightPipelineMeetingAnalyzer)

    def test_insight_pipeline_stage가_잘못되면_예외가_발생한다(self):
        with pytest.raises(ValueError):
            create_meeting_analyzer(
                "insight_pipeline",
                analyzer_chain=("rule_based", "unknown"),
            )

    def test_지원하지_않는_backend면_예외가_발생한다(self):
        with pytest.raises(ValueError):
            create_meeting_analyzer("unknown")
