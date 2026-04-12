"""세션 영역의 test session recovery service 동작을 검증한다."""
from server.app.domain.shared.enums import AudioSource, SessionMode, SessionStatus
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
)
from server.app.services.sessions.session_recovery_service import SessionRecoveryService
from server.app.services.sessions.session_service import SessionService


class _FakeLiveStreamService:
    def __init__(self, live_session_ids=None):
        self._live_session_ids = set(live_session_ids or [])

    def has_session_contexts(self, session_id: str) -> bool:
        return session_id in self._live_session_ids


class TestSessionRecoveryService:
    """고아 running 세션을 recovery 상태로 정리한다."""

    def test_running_세션에_runtime이_없으면_ended_복구상태로_전이한다(self, isolated_database):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        session_service = SessionService(session_repository)
        recovery_service = SessionRecoveryService(
            session_repository=session_repository,
            live_stream_service=_FakeLiveStreamService(),
        )

        session = session_service.create_session_draft(
            title="복구 대상 회의",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)

        recovered_count = recovery_service.recover_orphaned_running_sessions()
        recovered_session = session_repository.get_by_id(session.id)

        assert recovered_count == 1
        assert recovered_session is not None
        assert recovered_session.status == SessionStatus.ENDED
        assert recovered_session.recovery_required is True
        assert recovered_session.recovery_reason == "runtime_lost"
        assert recovered_session.recovery_detected_at is not None

    def test_running_세션에_runtime이_있으면_복구하지_않는다(self, isolated_database):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        session_service = SessionService(session_repository)
        session = session_service.create_session_draft(
            title="정상 실행 회의",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)

        recovery_service = SessionRecoveryService(
            session_repository=session_repository,
            live_stream_service=_FakeLiveStreamService({session.id}),
        )

        recovered_count = recovery_service.recover_orphaned_running_sessions()
        untouched_session = session_repository.get_by_id(session.id)

        assert recovered_count == 0
        assert untouched_session is not None
        assert untouched_session.status == SessionStatus.RUNNING
        assert untouched_session.recovery_required is False
