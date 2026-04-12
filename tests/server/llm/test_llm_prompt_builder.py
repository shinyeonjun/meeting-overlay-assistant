"""공통 영역의 test llm prompt builder 동작을 검증한다."""
from server.app.services.analysis.llm.contracts.llm_models import LLMAnalysisInput
from server.app.services.analysis.llm.extraction.llm_prompt_builder import (
    LLMAnalysisPromptBuilder,
)


class TestLLMAnalysisPromptBuilder:
    """프롬프트 생성 테스트."""

    def test_분석입력을_포함한_프롬프트를_생성한다(self):
        builder = LLMAnalysisPromptBuilder()

        prompt = builder.build(
            LLMAnalysisInput(
                session_id="session-test",
                utterance_id="utt-1",
                text="이번 배포에서는 이 수정은 제외합시다.",
            )
        )

        assert "출력은 반드시 JSON 객체 하나만 반환한다." in prompt
        assert '"session_id": "session-test"' in prompt
        assert '"utterance_id": "utt-1"' in prompt
        assert '"text": "이번 배포에서는 이 수정은 제외합시다."' in prompt
