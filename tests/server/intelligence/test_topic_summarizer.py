"""공통 영역의 test topic summarizer 동작을 검증한다."""
from server.app.services.sessions.topic_summarizer import NoOpTopicSummarizer


class TestNoOpTopicSummarizer:
    """NoOpTopicSummarizer 동작을 검증한다."""
    def test_최근_발화_묶음에서_반복되는_핵심_토큰을_요약한다(self):
        summarizer = NoOpTopicSummarizer()

        summary = summarizer.summarize(
            session_id="session-test",
            topic_texts=[
                "로그인 오류 원인을 먼저 분석해보죠",
                "로그인 화면에서 세션 만료 오류가 나는 것 같습니다",
                "오류가 사파리 로그인 처리에서 특히 자주 보입니다",
            ],
        )

        assert summary == "로그인 / 오류 논의"

    def test_반복_토큰이_없어도_최근_핵심어를_묶어_요약한다(self):
        summarizer = NoOpTopicSummarizer()

        summary = summarizer.summarize(
            session_id="session-test",
            topic_texts=["게임 전략 위치 선정 먼저 보죠"],
        )

        assert summary == "게임 / 전략 논의"
