"""공통 영역의 test completion client factory 동작을 검증한다."""
from __future__ import annotations

from server.app.services.analysis.llm.clients.noop_llm_completion_client import (
    NoOpLLMCompletionClient,
)
from server.app.services.analysis.llm.clients.ollama_completion_client import (
    OllamaCompletionClient,
)
from server.app.services.analysis.llm.factories.completion_client_factory import (
    create_llm_completion_client,
)


class TestCompletionClientFactory:
    """CompletionClientFactory 동작을 검증한다."""
    def test_noop_backend면_noop_client를_반환한다(self):
        client = create_llm_completion_client(
            backend_name="noop",
            model="ignored",
        )

        assert isinstance(client, NoOpLLMCompletionClient)

    def test_ollama_backend면_ollama_client를_반환한다(self):
        client = create_llm_completion_client(
            backend_name="ollama",
            model="qwen2.5:3b-instruct",
            base_url="http://127.0.0.1:11434/v1",
            timeout_seconds=10,
        )

        assert isinstance(client, OllamaCompletionClient)
