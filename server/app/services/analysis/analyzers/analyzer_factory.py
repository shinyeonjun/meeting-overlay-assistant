"""공통 영역의 analyzer factory 서비스를 제공한다."""
from __future__ import annotations

from collections.abc import Callable

from server.app.services.analysis.analyzers.analyzer import MeetingAnalyzer
from server.app.services.analysis.analyzers.fallback_meeting_analyzer import FallbackMeetingAnalyzer
from server.app.services.analysis.analyzers.insight_pipeline_meeting_analyzer import (
    InsightPipelineMeetingAnalyzer,
)
from server.app.services.analysis.analyzers.llm_based_meeting_analyzer import LLMBasedMeetingAnalyzer
from server.app.services.analysis.analyzers.rule_based_meeting_analyzer import RuleBasedMeetingAnalyzer
from server.app.services.analysis.llm.factories.llm_provider_factory import (
    create_llm_analysis_provider,
)


def create_meeting_analyzer(
    backend_name: str,
    rules_config_path: str | None = None,
    llm_provider_backend: str = "noop",
    llm_model: str = "gpt-4o-mini",
    llm_base_url: str = "http://127.0.0.1:11434/v1",
    llm_api_key: str | None = None,
    llm_timeout_seconds: float = 20.0,
    analyzer_chain: tuple[str, ...] | None = None,
) -> MeetingAnalyzer:
    """설정값에 맞는 회의 분석기 구현체를 반환한다."""

    def _create_llm_analyzer() -> MeetingAnalyzer:
        return LLMBasedMeetingAnalyzer(
            provider=create_llm_analysis_provider(
                backend_name=llm_provider_backend,
                model=llm_model,
                base_url=llm_base_url,
                api_key=llm_api_key,
                timeout_seconds=llm_timeout_seconds,
            )
        )

    base_analyzer_builders: dict[str, Callable[[], MeetingAnalyzer]] = {
        "rule_based": lambda: RuleBasedMeetingAnalyzer(rules_config_path=rules_config_path),
        "llm": _create_llm_analyzer,
        "hybrid": lambda: FallbackMeetingAnalyzer(
            (
                _create_llm_analyzer(),
                RuleBasedMeetingAnalyzer(rules_config_path=rules_config_path),
            )
        ),
    }

    def _create_insight_pipeline_analyzer() -> MeetingAnalyzer:
        stage_backends = analyzer_chain or ("rule_based", "llm")
        analyzers: list[MeetingAnalyzer] = []
        for stage_backend in stage_backends:
            builder = base_analyzer_builders.get(stage_backend)
            if builder is None:
                raise ValueError(
                    f"insight pipeline stage backend를 지원하지 않습니다: {stage_backend}"
                )
            analyzers.append(builder())
        return InsightPipelineMeetingAnalyzer(tuple(analyzers))

    analyzer_builders: dict[str, Callable[[], MeetingAnalyzer]] = {
        **base_analyzer_builders,
        "insight_pipeline": _create_insight_pipeline_analyzer,
    }

    builder = analyzer_builders.get(backend_name)
    if builder is None:
        raise ValueError(f"지원하지 않는 analyzer backend입니다: {backend_name}")
    return builder()
