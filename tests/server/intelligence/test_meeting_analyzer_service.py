"""공통 영역의 test meeting analyzer service 동작을 검증한다."""
from server.app.domain.shared.enums import EventType
from server.app.services.analysis.llm.contracts.llm_models import (
    LLMAnalysisInput,
    LLMAnalysisResult,
    LLMEventCandidate,
)
from server.app.services.analysis.llm.contracts.llm_provider import LLMAnalysisProvider
from server.app.services.analysis.analyzers.llm_based_meeting_analyzer import (
    LLMBasedMeetingAnalyzer,
)
from server.app.services.analysis.analyzers.rule_based_meeting_analyzer import (
    RuleBasedMeetingAnalyzer,
)
from tests.fixtures.support.sample_inputs import (
    ACTION_TEXT,
    DECISION_TEXT,
    QUESTION_TEXT,
    RISK_TEXT,
    TOPIC_TEXT,
    build_utterance,
)


class TestRuleBasedMeetingAnalyzer:
    """규칙 기반 분석기 테스트."""

    def test_일반_설명_발화는_기본적으로_topic_이벤트를_즉시_만들지_않는다(self):
        service = RuleBasedMeetingAnalyzer()

        events = service.analyze(build_utterance(TOPIC_TEXT))

        assert events == []

    def test_짧고_반복적인_문장은_topic_이벤트로_생성하지_않는다(self):
        service = RuleBasedMeetingAnalyzer()

        events = service.analyze(build_utterance("자리 자리 자리 넓게 넓게"))

        assert events == []

    def test_숫자_비중이_높은_문장은_topic_이벤트로_생성하지_않는다(self):
        service = RuleBasedMeetingAnalyzer()

        events = service.analyze(build_utterance("3 6 9 10 12 순서로 먼저 배치하고"))

        assert events == []

    def test_리스크_발화를_입력하면_risk_이벤트를_생성하고_topic으로_중복_분류하지_않는다(self):
        service = RuleBasedMeetingAnalyzer()

        events = service.analyze(build_utterance(RISK_TEXT))

        assert len(events) == 1
        assert events[0].event_type == EventType.RISK
        assert events[0].state.value == "open"

    def test_질문_발화를_입력하면_question_이벤트를_생성한다(self):
        service = RuleBasedMeetingAnalyzer()

        events = service.analyze(build_utterance(QUESTION_TEXT))

        assert len(events) == 1
        assert events[0].event_type == EventType.QUESTION
        assert events[0].state.value == "open"

    def test_결정_발화를_입력하면_decision_이벤트를_생성한다(self):
        service = RuleBasedMeetingAnalyzer()

        events = service.analyze(build_utterance(DECISION_TEXT))

        assert len(events) == 1
        assert events[0].event_type == EventType.DECISION
        assert events[0].state.value == "confirmed"

    def test_액션_발화를_입력하면_action_item_이벤트를_생성한다(self):
        service = RuleBasedMeetingAnalyzer()

        events = service.analyze(build_utterance(ACTION_TEXT))

        assert len(events) == 1
        assert events[0].event_type == EventType.ACTION_ITEM
        assert events[0].state.value == "open"


class TestLLMBasedMeetingAnalyzer:
    """LLM 기반 분석기 뼈대 테스트."""

    def test_현재_llm_분석기는_빈_이벤트를_반환한다(self):
        service = LLMBasedMeetingAnalyzer()

        events = service.analyze(build_utterance(QUESTION_TEXT))

        assert events == []

    def test_llm_provider_결과를_event로_변환한다(self):
        service = LLMBasedMeetingAnalyzer(
            provider=StubLLMAnalysisProvider(
                LLMAnalysisResult(
                    candidates=[
                        LLMEventCandidate(
                            event_type="decision",
                            title=DECISION_TEXT,
                            body="LLM이 결정 사항으로 해석했습니다.",
                            state="confirmed",
                        )
                    ]
                )
            )
        )

        events = service.analyze(build_utterance(DECISION_TEXT))

        assert len(events) == 1
        assert events[0].event_type == EventType.DECISION
        assert events[0].title == DECISION_TEXT
        assert events[0].state.value == "confirmed"

    def test_llm_provider가_알수없는_이벤트타입을_주면_무시한다(self):
        service = LLMBasedMeetingAnalyzer(
            provider=StubLLMAnalysisProvider(
                LLMAnalysisResult(
                    candidates=[
                        LLMEventCandidate(
                            event_type="unknown",
                            title="알수없는 이벤트",
                            state="open",
                        )
                    ]
                )
            )
        )

        events = service.analyze(build_utterance("알수없는 이벤트 예시"))

        assert events == []


class StubLLMAnalysisProvider(LLMAnalysisProvider):
    """테스트용 LLM provider."""

    def __init__(self, result: LLMAnalysisResult) -> None:
        self._result = result
        self.last_input: LLMAnalysisInput | None = None

    def analyze(self, analysis_input: LLMAnalysisInput) -> LLMAnalysisResult:
        self.last_input = analysis_input
        return self._result
