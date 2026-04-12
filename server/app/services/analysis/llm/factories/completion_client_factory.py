"""공통 영역의 completion client factory 서비스를 제공한다."""
from __future__ import annotations

from collections.abc import Callable

from server.app.services.analysis.llm.clients.noop_llm_completion_client import (
    NoOpLLMCompletionClient,
)
from server.app.services.analysis.llm.clients.ollama_completion_client import (
    OllamaCompletionClient,
)
from server.app.services.analysis.llm.clients.openai_compatible_completion_client import (
    OpenAICompatibleCompletionClient,
)
from server.app.services.analysis.llm.clients.openai_responses_completion_client import (
    OpenAIResponsesCompletionClient,
)
from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)


def create_llm_completion_client(
    backend_name: str,
    model: str,
    base_url: str = "http://127.0.0.1:11434/v1",
    api_key: str | None = None,
    timeout_seconds: float = 20.0,
) -> LLMCompletionClient:
    """설정값에 맞는 completion client를 반환한다."""

    builders: dict[str, Callable[[], LLMCompletionClient]] = {
        "noop": NoOpLLMCompletionClient,
        "ollama": lambda: OllamaCompletionClient(
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        ),
        "local_openai_compatible": lambda: OpenAICompatibleCompletionClient(
            model=model,
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        ),
        "openai_compatible": lambda: OpenAICompatibleCompletionClient(
            model=model,
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        ),
        "openai": lambda: OpenAIResponsesCompletionClient(model=model),
    }

    builder = builders.get(backend_name)
    if builder is None:
        raise ValueError(f"지원하지 않는 llm completion backend입니다: {backend_name}")
    return builder()
