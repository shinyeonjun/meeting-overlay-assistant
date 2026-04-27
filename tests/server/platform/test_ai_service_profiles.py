from __future__ import annotations

from dataclasses import replace

from server.app.core.ai_service_profiles import (
    resolve_analyzer_service_profile,
    resolve_live_analyzer_service_profile,
    resolve_post_processing_analyzer_service_profile,
    resolve_report_analyzer_service_profile,
    resolve_topic_summarizer_service_profile,
    resolve_workspace_summary_synthesizer_service_profile,
)
from server.app.core.config import settings


class TestAIServiceProfiles:
    def test_analyzer_profile은_completion_client_설정을_함께_해석한다(self):
        profile = resolve_analyzer_service_profile(settings)

        assert profile.backend_name in {"noop", "rule_based", "llm", "hybrid", "insight_pipeline"}
        assert profile.completion_client.backend_name
        assert profile.completion_client.model
        assert isinstance(profile.analyzer_stages, tuple)

    def test_insight_pipeline_profile은_stage_체인을_해석한다(self):
        profile = resolve_analyzer_service_profile(
            replace(settings, analyzer_backend="insight_pipeline")
        )

        assert profile.backend_name == "insight_pipeline"
        assert profile.analyzer_stages == ("rule_based", "llm")

    def test_live_analyzer_profile은_noop으로_분리된다(self):
        profile = resolve_live_analyzer_service_profile(
            replace(settings, live_analyzer_backend="noop")
        )

        assert profile.backend_name == "noop"
        assert profile.analyzer_stages == ()

    def test_post_processing_analyzer_profile은_rule_based를_기본으로_사용한다(self):
        profile = resolve_post_processing_analyzer_service_profile(
            replace(settings, post_processing_analyzer_backend="rule_based")
        )

        assert profile.backend_name == "rule_based"
        assert profile.analyzer_stages == ()

    def test_post_processing_analyzer_profile은_실험_옵션으로_insight_pipeline을_지원한다(self):
        profile = resolve_post_processing_analyzer_service_profile(
            replace(settings, post_processing_analyzer_backend="insight_pipeline")
        )

        assert profile.backend_name == "insight_pipeline"
        assert profile.analyzer_stages == ("rule_based", "llm")

    def test_report_analyzer_profile은_rule_based로_분리된다(self):
        profile = resolve_report_analyzer_service_profile(
            replace(settings, report_analyzer_backend="rule_based")
        )

        assert profile.backend_name == "rule_based"
        assert profile.analyzer_stages == ()

    def test_topic_summarizer_profile은_요약기_completion_profile을_해석한다(self):
        profile = resolve_topic_summarizer_service_profile(settings)

        assert profile.backend_name
        assert profile.completion_client.backend_name

    def test_workspace_summary_profile은_completion_profile을_해석한다(self):
        profile = resolve_workspace_summary_synthesizer_service_profile(settings)

        assert profile.backend_name
        assert profile.completion_client.backend_name
        assert profile.completion_client.model
