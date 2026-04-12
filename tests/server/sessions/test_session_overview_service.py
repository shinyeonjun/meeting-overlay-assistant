"""세션 overview 서비스 테스트."""

from __future__ import annotations

from server.app.domain.session import MeetingSession
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import AudioSource, SessionMode
from server.app.services.sessions.overview_builder import SessionOverviewBuilder
from server.app.services.sessions.session_overview_service import SessionOverviewService


class _StubSessionRepository:
    def __init__(self, session: MeetingSession) -> None:
        self._session = session

    def get_by_id(self, session_id: str):
        if session_id == self._session.id:
            return self._session
        return None


class _StubEventRepository:
    def list_by_session(self, session_id: str):
        del session_id
        return []


class _StubUtteranceRepository:
    def __init__(self, utterances: list[Utterance]) -> None:
        self._utterances = utterances

    def list_recent_by_session(self, session_id: str, limit: int, *, connection=None):
        del session_id, connection
        return self._utterances[-limit:]


class _RecordingTopicSummarizer:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def summarize(self, session_id: str, topic_texts: list[str], fallback_topic: str | None = None):
        del session_id, fallback_topic
        self.calls.append(topic_texts)
        return "로그인 오류 논의"


class TestSessionOverviewService:
    def test_recent_utterances에서_긴_발화만_topic_요약기로_전달된다(self):
        session = MeetingSession.start(
            title="overview service 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        utterances = [
            Utterance.create(
                session_id=session.id,
                seq_num=1,
                start_ms=0,
                end_ms=1000,
                text="짧다",
                confidence=0.95,
                input_source="system_audio",
                latency_ms=120,
            ),
            Utterance.create(
                session_id=session.id,
                seq_num=2,
                start_ms=1000,
                end_ms=2000,
                text="로그인 화면에서 세션 만료 오류가 납니다",
                confidence=0.71,
                input_source="system_audio",
                latency_ms=80,
            ),
            Utterance.create(
                session_id=session.id,
                seq_num=3,
                start_ms=2000,
                end_ms=3000,
                text="오류가 사파리 브라우저에서 자주 보입니다",
                confidence=0.74,
                input_source="mic",
                latency_ms=100,
            ),
            Utterance.create(
                session_id=session.id,
                seq_num=4,
                start_ms=3000,
                end_ms=4000,
                text="이건 신뢰도 낮은 문장입니다",
                confidence=0.32,
                input_source="mic",
                latency_ms=None,
            ),
        ]
        topic_summarizer = _RecordingTopicSummarizer()
        service = SessionOverviewService(
            session_repository=_StubSessionRepository(session),
            event_repository=_StubEventRepository(),
            utterance_repository=_StubUtteranceRepository(utterances),
            overview_builder=SessionOverviewBuilder(),
            topic_summarizer=topic_summarizer,
            recent_topic_utterance_count=5,
            min_topic_utterance_length=10,
            min_topic_utterance_confidence=0.58,
        )

        overview = service.build_overview(session.id)

        assert overview.current_topic == "로그인 오류 논의"
        assert topic_summarizer.calls == [[
            "로그인 화면에서 세션 만료 오류가 납니다",
            "오류가 사파리 브라우저에서 자주 보입니다",
        ]]
        assert overview.recent_average_latency_ms == 100.0
        assert overview.recent_utterance_count_by_source == {
            "system_audio": 2,
            "mic": 2,
        }

    def test_latency가_없으면_평균_latency는_none이다(self):
        session = MeetingSession.start(
            title="overview latency none 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        utterances = [
            Utterance.create(
                session_id=session.id,
                seq_num=1,
                start_ms=0,
                end_ms=1000,
                text="첫 번째",
                confidence=0.95,
                input_source="system_audio",
                latency_ms=None,
            ),
            Utterance.create(
                session_id=session.id,
                seq_num=2,
                start_ms=1000,
                end_ms=2000,
                text="두 번째",
                confidence=0.95,
                input_source=None,
                latency_ms=None,
            ),
        ]
        service = SessionOverviewService(
            session_repository=_StubSessionRepository(session),
            event_repository=_StubEventRepository(),
            utterance_repository=_StubUtteranceRepository(utterances),
            overview_builder=SessionOverviewBuilder(),
            topic_summarizer=_RecordingTopicSummarizer(),
        )

        overview = service.build_overview(session.id)

        assert overview.recent_average_latency_ms is None
        assert overview.recent_utterance_count_by_source == {
            "system_audio": 1,
            "unknown": 1,
        }
