"""공통 영역의 test overview builder 동작을 검증한다."""
from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import AudioSource, EventType, SessionMode
from server.app.services.sessions.overview_builder import SessionOverviewBuilder


class TestSessionOverviewBuilder:
    """세션 overview 조립 테스트."""

    def test_이벤트_목록을_유형별_overview로_정리한다(self):
        builder = SessionOverviewBuilder()
        session = MeetingSession.start(
            title="overview builder 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        events = [
            MeetingEvent.create(
                session_id=session.id,
                event_type=EventType.TOPIC,
                title="로그인 오류 원인을 먼저 분석해보죠",
                body=None,
                state="active",
                priority=60,
                source_utterance_id="utt-1",
            ),
            MeetingEvent.create(
                session_id=session.id,
                event_type=EventType.QUESTION,
                title="이거 사파리에서만 재현되는 거 맞아요?",
                body=None,
                state="open",
                priority=70,
                source_utterance_id="utt-2",
            ),
        ]

        overview = builder.build(session=session, events=events)

        assert overview.session.id == session.id
        assert overview.current_topic == "로그인 오류 원인을 먼저 분석해보죠"
        assert len(overview.questions) == 1
        assert overview.questions[0].title == "이거 사파리에서만 재현되는 거 맞아요?"

    def test_여러_topic_발화가_쌓이면_반복_키워드_기반_주제를_요약한다(self):
        builder = SessionOverviewBuilder()
        session = MeetingSession.start(
            title="topic summary 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        events = [
            MeetingEvent.create(
                session_id=session.id,
                event_type=EventType.TOPIC,
                title="로그인 오류 원인을 먼저 분석해보죠",
                body=None,
                state="active",
                priority=60,
                source_utterance_id="utt-1",
            ),
            MeetingEvent.create(
                session_id=session.id,
                event_type=EventType.TOPIC,
                title="로그인 흐름에서 세션 만료 오류가 나는 것 같습니다",
                body=None,
                state="active",
                priority=60,
                source_utterance_id="utt-2",
            ),
            MeetingEvent.create(
                session_id=session.id,
                event_type=EventType.TOPIC,
                title="오류가 사파리 로그인 처리에서 특히 자주 보입니다",
                body=None,
                state="active",
                priority=60,
                source_utterance_id="utt-3",
            ),
        ]

        overview = builder.build(session=session, events=events)

        assert overview.current_topic == "로그인 / 오류 논의"
