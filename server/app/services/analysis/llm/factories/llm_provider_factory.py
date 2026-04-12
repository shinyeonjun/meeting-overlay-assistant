"""LLM provider 생성 팩토리."""

from __future__ import annotations

from collections.abc import Callable

from server.app.services.analysis.llm.contracts.llm_provider import LLMAnalysisProvider
from server.app.services.analysis.llm.factories.completion_client_factory import (
    create_llm_completion_client,
)
from server.app.services.analysis.llm.providers.noop_llm_analysis_provider import (
    NoOpLLMAnalysisProvider,
)
from server.app.services.analysis.llm.providers.prompt_based_llm_analysis_provider import (
    PromptBasedLLMAnalysisProvider,
)


def create_llm_analysis_provider(
    backend_name: str,
    model: str,
    base_url: str = "http://127.0.0.1:11434/v1",
    api_key: str | None = None,
    timeout_seconds: float = 20.0,
) -> LLMAnalysisProvider:
    """설정값에 맞는 LLM provider를 반환한다."""
    builders: dict[str, Callable[[], LLMAnalysisProvider]] = {
        "noop": NoOpLLMAnalysisProvider,
        "ollama": lambda: PromptBasedLLMAnalysisProvider(
            completion_client=create_llm_completion_client(
                backend_name="ollama",
                model=model,
                base_url=base_url,
                api_key=api_key,
                timeout_seconds=timeout_seconds,
            ),
            backend_name="ollama",
        ),
        "local_openai_compatible": lambda: PromptBasedLLMAnalysisProvider(
            completion_client=create_llm_completion_client(
                backend_name="local_openai_compatible",
                model=model,
                base_url=base_url,
                api_key=api_key,
                timeout_seconds=timeout_seconds,
            ),
            backend_name="local_openai_compatible",
        ),
        "openai_compatible": lambda: PromptBasedLLMAnalysisProvider(
            completion_client=create_llm_completion_client(
                backend_name="openai_compatible",
                model=model,
                base_url=base_url,
                api_key=api_key,
                timeout_seconds=timeout_seconds,
            ),
            backend_name="openai_compatible",
        ),
        "openai": lambda: PromptBasedLLMAnalysisProvider(
            completion_client=create_llm_completion_client(
                backend_name="openai",
                model=model,
                base_url=base_url,
                api_key=api_key,
                timeout_seconds=timeout_seconds,
            ),
            backend_name="openai",
        ),
    }

    builder = builders.get(backend_name)
    if builder is None:
        raise ValueError(f"지원하지 않는 llm provider backend입니다: {backend_name}")
    return builder()
