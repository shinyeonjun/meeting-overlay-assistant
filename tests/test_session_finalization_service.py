"""세션 종료 orchestration 테스트"""

from backend.app.domain.shared.enums import AudioSource, SessionMode, SessionStatus
from backend.app.infrastructure.persistence.sqlite.database import Database
from backend.app.infrastructure.persistence.sqlite.repositories.session_repository import (
    SQLiteSessionRepository,
)
from backend.app.services.sessions.session_finalization_service import (
    SessionFinalizationService,
)
from backend.app.services.sessions.session_service import SessionService


class _UnusedReportService:
    pass


class TestSessionFinalizationService:
    """세션 종료가 리포트 자동 생성 없이 끝나는지 검증한다."""

    def test_세션_종료는_세션_상태만_ended로_바꾼다(self, tmp_path):
        database = Database(tmp_path / "test.db")
        database.initialize()
        session_repository = SQLiteSessionRepository(database)
        session_service = SessionService(session_repository)
        finalization_service = SessionFinalizationService(session_service, _UnusedReportService())
        session = session_service.start_session(
            title="테스트 회의",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )

        ended_session = finalization_service.finalize_session(session.id)

        assert ended_session.status == SessionStatus.ENDED
        assert ended_session.ended_at is not None
