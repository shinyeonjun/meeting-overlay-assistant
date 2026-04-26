"""실시간 질문 LLM 클라이언트 테스트."""

from __future__ import annotations

from server.app.services.live_questions.models import (
    LiveQuestionRequest,
    LiveQuestionUtterance,
)
from server.app.services.live_questions.question_llm_client import LiveQuestionLLMClient
from server.app.services.live_questions.question_prompt_builder import (
    LIVE_QUESTION_RESPONSE_SCHEMA,
    build_question_analysis_system_prompt,
    build_question_analysis_warmup_prompt,
)


class TestLiveQuestionLLMClient:
    """질문 전용 schema/keep_alive 전달을 검증한다."""

    def test_schema와_keep_alive를_항상_질문분석에_전달한다(self, monkeypatch):
        captured: dict[str, object] = {}

        class FakeCompletionClient:
            def complete(
                self,
                prompt: str,
                *,
                system_prompt: str | None = None,
                response_schema: dict[str, object] | None = None,
                keep_alive: str | None = None,
            ) -> str:
                captured["prompt"] = prompt
                captured["system_prompt"] = system_prompt
                captured["response_schema"] = response_schema
                captured["keep_alive"] = keep_alive
                return '{"operations":[]}'

        monkeypatch.setattr(
            "server.app.services.live_questions.question_llm_client.create_llm_completion_client",
            lambda **kwargs: FakeCompletionClient(),
        )

        client = LiveQuestionLLMClient(
            backend_name="ollama",
            model="qwen2.5:3b-instruct",
            base_url="http://127.0.0.1:11434/v1",
            api_key=None,
            timeout_seconds=20.0,
            keep_alive="30m",
        )
        request = LiveQuestionRequest.create(
            session_id="s-1",
            utterances=[
                LiveQuestionUtterance(
                    id="u-1",
                    text="이번 일정 언제 확정되나요?",
                    speaker_label=None,
                    timestamp_ms=1000,
                    confidence=0.92,
                )
            ],
            open_questions=[],
        )

        result = client.analyze(request)

        assert result.operations == ()
        assert captured["keep_alive"] == "30m"
        assert captured["response_schema"] == LIVE_QUESTION_RESPONSE_SCHEMA
        assert captured["system_prompt"] == build_question_analysis_system_prompt()

    def test_close_operation은_mvp_질문_감지에서_버린다(self, monkeypatch):
        class FakeCompletionClient:
            def complete(
                self,
                prompt: str,
                *,
                system_prompt: str | None = None,
                response_schema: dict[str, object] | None = None,
                keep_alive: str | None = None,
            ) -> str:
                return (
                    '{"operations":['
                    '{"op":"close","summary":null,"confidence":0.9,'
                    '"evidence_utterance_ids":[],"target_question_id":"q-1",'
                    '"speaker_label":null,"reason":"answered"},'
                    '{"op":"add","summary":"배포 일정은 언제 확정되나요?",'
                    '"confidence":0.92,"evidence_utterance_ids":["u-1"],'
                    '"target_question_id":null,"speaker_label":"SPEAKER_00",'
                    '"reason":"question"}'
                    "]}"
                )

        monkeypatch.setattr(
            "server.app.services.live_questions.question_llm_client.create_llm_completion_client",
            lambda **kwargs: FakeCompletionClient(),
        )

        client = LiveQuestionLLMClient(
            backend_name="ollama",
            model="qwen2.5:3b-instruct",
            base_url="http://127.0.0.1:11434/v1",
            api_key=None,
            timeout_seconds=20.0,
        )
        request = LiveQuestionRequest.create(
            session_id="s-1",
            utterances=[
                LiveQuestionUtterance(
                    id="u-1",
                    text="배포 일정은 언제 확정되나요?",
                    speaker_label="SPEAKER_00",
                    timestamp_ms=1000,
                    confidence=0.92,
                )
            ],
            open_questions=[],
        )

        result = client.analyze(request)

        assert len(result.operations) == 1
        assert result.operations[0].op == "add"
        assert result.operations[0].target_question_id is None

    def test_warm_up이_schema와_keep_alive를_같이_전달한다(self, monkeypatch):
        captured: dict[str, object] = {}

        class FakeCompletionClient:
            def complete(
                self,
                prompt: str,
                *,
                system_prompt: str | None = None,
                response_schema: dict[str, object] | None = None,
                keep_alive: str | None = None,
            ) -> str:
                captured["prompt"] = prompt
                captured["system_prompt"] = system_prompt
                captured["response_schema"] = response_schema
                captured["keep_alive"] = keep_alive
                return '{"operations":[]}'

        monkeypatch.setattr(
            "server.app.services.live_questions.question_llm_client.create_llm_completion_client",
            lambda **kwargs: FakeCompletionClient(),
        )

        client = LiveQuestionLLMClient(
            backend_name="ollama",
            model="qwen2.5:3b-instruct",
            base_url="http://127.0.0.1:11434/v1",
            api_key=None,
            timeout_seconds=20.0,
            keep_alive="30m",
        )

        client.warm_up()

        assert captured["prompt"] == build_question_analysis_warmup_prompt()
        assert captured["keep_alive"] == "30m"
        assert captured["response_schema"] == LIVE_QUESTION_RESPONSE_SCHEMA
        assert captured["system_prompt"] == build_question_analysis_system_prompt()
