"""세션 종료 orchestration 테스트"""

from server.app.domain.shared.enums import AudioSource, SessionMode, SessionStatus
from server.app.infrastructure.persistence.sqlite.database import Database
from server.app.infrastructure.persistence.sqlite.repositories.meeting_context_repository import (
    SQLiteMeetingContextRepository,
)
from server.app.infrastructure.persistence.sqlite.repositories.participation import (
    SQLiteParticipantFollowupRepository,
)
from server.app.infrastructure.persistence.sqlite.repositories.report_generation_job_repository import (
    SQLiteReportGenerationJobRepository,
)
from server.app.infrastructure.persistence.sqlite.repositories.session import (
    SQLiteSessionRepository,
)
from server.app.services.participation.participant_followup_service import (
    ParticipantFollowupService,
)
from server.app.services.participation.participant_resolution_service import (
    ParticipantResolutionService,
)
from server.app.services.reports.jobs.report_generation_job_service import (
    ReportGenerationJobService,
)
from server.app.services.sessions.session_finalization_service import (
    SessionFinalizationService,
)
from server.app.services.sessions.session_service import SessionService


class _UnusedReportService:
    pass


class TestSessionFinalizationService:
    """세션 종료가 리포트 자동 생성 없이 끝나는지 검증한다."""

    def test_세션_종료는_세션_상태만_ended로_바꾼다(self, tmp_path):
        database = Database(tmp_path / "test.db")
        database.initialize()
        session_repository = SQLiteSessionRepository(database)
        session_service = SessionService(session_repository)
        participant_followup_service = ParticipantFollowupService(
            participant_followup_repository=SQLiteParticipantFollowupRepository(database),
            participant_resolution_service=ParticipantResolutionService(
                meeting_context_repository=SQLiteMeetingContextRepository(database),
            ),
        )
        report_generation_job_service = ReportGenerationJobService(
            repository=SQLiteReportGenerationJobRepository(database),
            report_service=_UnusedReportService(),
        )
        finalization_service = SessionFinalizationService(
            session_service,
            report_generation_job_service,
            participant_followup_service,
        )
        session = session_service.create_session_draft(
            title="테스트 회의",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)

        ended_session = finalization_service.finalize_session(session.id)

        assert ended_session.status == SessionStatus.ENDED
        assert ended_session.ended_at is not None
        latest_job = report_generation_job_service.get_latest_job(session.id)
        assert latest_job is not None
        assert latest_job.status == "pending"

    def test_세션_종료시_미해결_참여자_followup을_생성한다(self, tmp_path):
        database = Database(tmp_path / "test.db")
        database.initialize()
        session_repository = SQLiteSessionRepository(database)
        participant_followup_service = ParticipantFollowupService(
            participant_followup_repository=SQLiteParticipantFollowupRepository(database),
            participant_resolution_service=ParticipantResolutionService(
                meeting_context_repository=SQLiteMeetingContextRepository(database),
            ),
        )
        session_service = SessionService(session_repository)
        report_generation_job_service = ReportGenerationJobService(
            repository=SQLiteReportGenerationJobRepository(database),
            report_service=_UnusedReportService(),
        )
        finalization_service = SessionFinalizationService(
            session_service,
            report_generation_job_service,
            participant_followup_service,
        )

        session = session_service.create_session_draft(
            title="후속 작업 생성 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
            participants=["김영희"],
        )
        session = session_service.start_session(session.id)

        finalization_service.finalize_session(session.id)
        finalization_service.finalize_session(session.id)

        followups = participant_followup_service.list_followups(session_id=session.id)

        assert len(followups) == 1
        assert followups[0].participant_name == "김영희"
        assert followups[0].resolution_status == "unmatched"
        assert followups[0].followup_status == "pending"
