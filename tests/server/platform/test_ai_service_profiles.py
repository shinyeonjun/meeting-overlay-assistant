from __future__ import annotations

from dataclasses import replace

from server.app.core.ai_service_profiles import (
    resolve_analyzer_service_profile,
    resolve_report_refiner_service_profile,
    resolve_topic_summarizer_service_profile,
)
from server.app.core.config import settings


class TestAIServiceProfiles:
    def test_analyzer_profile은_completion_client_설정을_함께_해석한다(self):
        profile = resolve_analyzer_service_profile(settings)

        assert profile.backend_name in {"rule_based", "llm", "hybrid", "insight_pipeline"}
        assert profile.completion_client.backend_name
        assert profile.completion_client.model
        assert isinstance(profile.analyzer_stages, tuple)

    def test_insight_pipeline_profile은_stage_체인을_해석한다(self):
        profile = resolve_analyzer_service_profile(
            replace(settings, analyzer_backend="insight_pipeline")
        )

        assert profile.backend_name == "insight_pipeline"
        assert profile.analyzer_stages == ("rule_based", "llm")

    def test_report_refiner_profile은_noop이어도_completion_profile을_반환한다(self):
        profile = resolve_report_refiner_service_profile(settings)

        assert profile.backend_name
        assert profile.completion_client.backend_name

    def test_topic_summarizer_profile은_요약기_completion_profile을_해석한다(self):
        profile = resolve_topic_summarizer_service_profile(settings)

        assert profile.backend_name
        assert profile.completion_client.backend_name

    def test_llm_env를_직접_지정하면_profile보다_우선한다(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "qwen3:4b")
        monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:9999/v1")

        profile = resolve_analyzer_service_profile(
            replace(settings, analyzer_backend="insight_pipeline")
        )

        assert profile.completion_client.model == "qwen3:4b"
        assert profile.completion_client.base_url == "http://127.0.0.1:9999/v1"

    def test_llm_env가_비어_있으면_profile_값을_쓴다(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "")
        monkeypatch.delenv("LLM_BASE_URL", raising=False)

        profile = resolve_analyzer_service_profile(
            replace(settings, analyzer_backend="insight_pipeline", llm_model="fallback-model")
        )

        assert profile.completion_client.model == "qwen2.5:3b-instruct"
