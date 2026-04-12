"""공통 영역의 test llm provider factory 동작을 검증한다."""
import pytest

from server.app.services.analysis.llm.factories.llm_provider_factory import (
    create_llm_analysis_provider,
)
from server.app.services.analysis.llm.providers.noop_llm_analysis_provider import (
    NoOpLLMAnalysisProvider,
)
from server.app.services.analysis.llm.providers.prompt_based_llm_analysis_provider import (
    PromptBasedLLMAnalysisProvider,
)


class TestLLMProviderFactory:
    """LLM provider 팩토리 동작을 검증한다."""

    def test_noop_backend를_선택하면_noop_provider를_반환한다(self):
        provider = create_llm_analysis_provider("noop", model="dummy")

        assert isinstance(provider, NoOpLLMAnalysisProvider)

    def test_local_openai_compatible_backend를_선택하면_prompt_based_provider를_반환한다(self):
        provider = create_llm_analysis_provider(
            "local_openai_compatible",
            model="phi-local",
            base_url="http://127.0.0.1:1234/v1",
        )

        assert isinstance(provider, PromptBasedLLMAnalysisProvider)

    def test_ollama_backend를_선택하면_prompt_based_provider를_반환한다(self):
        provider = create_llm_analysis_provider(
            "ollama",
            model="qwen2.5:3b-instruct",
            base_url="http://127.0.0.1:11434/v1",
        )

        assert isinstance(provider, PromptBasedLLMAnalysisProvider)

    def test_지원하지_않는_backend를_선택하면_예외가_발생한다(self):
        with pytest.raises(ValueError):
            create_llm_analysis_provider("unknown", model="dummy")
