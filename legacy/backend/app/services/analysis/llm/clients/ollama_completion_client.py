"""Ollama 전용 completion client."""

from __future__ import annotations

from backend.app.services.analysis.llm.clients.openai_compatible_completion_client import (
    OpenAICompatibleCompletionClient,
)


class OllamaCompletionClient(OpenAICompatibleCompletionClient):
    """Ollama의 OpenAI 호환 API를 호출한다."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434/v1",
        timeout_seconds: float = 20.0,
    ) -> None:
        super().__init__(
            model=model,
            base_url=base_url,
            api_key=None,
            timeout_seconds=timeout_seconds,
        )
