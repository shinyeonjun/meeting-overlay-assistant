"""공통 영역의 test prompt based llm analysis provider 동작을 검증한다."""
from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.analysis.llm.contracts.llm_models import LLMAnalysisInput
from server.app.services.analysis.llm.providers.prompt_based_llm_analysis_provider import (
    PromptBasedLLMAnalysisProvider,
)


class TestPromptBasedLLMAnalysisProvider:
    """프롬프트 기반 provider 조합 테스트."""

    def test_completion_client_응답을_분석결과로_변환한다(self):
        provider = PromptBasedLLMAnalysisProvider(
            completion_client=StubCompletionClient(
                '{"candidates":[{"event_type":"question","title":"이거 사파리에서만 재현되는 거 맞아요?","state":"open","priority":70}]}'
            )
        )

        result = provider.analyze(
            LLMAnalysisInput(
                session_id="session-test",
                utterance_id="utt-1",
                text="이거 사파리에서만 재현되는 거 맞아요?",
            )
        )

        assert len(result.candidates) == 1
        assert result.candidates[0].event_type == "question"
        assert result.candidates[0].state == "open"


class StubCompletionClient(LLMCompletionClient):
    """테스트용 completion client."""

    def __init__(self, response_text: str) -> None:
        self._response_text = response_text

    def complete(self, prompt: str) -> str:
        assert "출력은 반드시 JSON 객체 하나만 반환한다." in prompt
        return self._response_text
