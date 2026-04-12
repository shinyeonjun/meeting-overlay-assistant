"""세션 종료 orchestration 테스트."""

from server.app.domain.shared.enums import AudioSource, SessionMode, SessionStatus
from server.app.infrastructure.persistence.postgresql.repositories.context import (
    PostgreSQLMeetingContextRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.participation import (
    PostgreSQLParticipantFollowupRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_report_generation_job_repository import (
    PostgreSQLReportGenerationJobRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
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
    """세션 종료는 상태 정리와 후속 조치만 수행한다."""

    def test_세션_종료는_세션_상태만_ended로_바꾼다(self, isolated_database):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        session_service = SessionService(session_repository)
        participant_followup_service = ParticipantFollowupService(
            participant_followup_repository=PostgreSQLParticipantFollowupRepository(
                isolated_database
            ),
            participant_resolution_service=ParticipantResolutionService(
                meeting_context_repository=PostgreSQLMeetingContextRepository(
                    isolated_database
                ),
            ),
        )
        report_generation_job_service = ReportGenerationJobService(
            repository=PostgreSQLReportGenerationJobRepository(isolated_database),
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
        assert latest_job is None

    def test_세션_종료는_미해결_참여자_followup을_생성한다(self, isolated_database):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        participant_followup_service = ParticipantFollowupService(
            participant_followup_repository=PostgreSQLParticipantFollowupRepository(
                isolated_database
            ),
            participant_resolution_service=ParticipantResolutionService(
                meeting_context_repository=PostgreSQLMeetingContextRepository(
                    isolated_database
                ),
            ),
        )
        session_service = SessionService(session_repository)
        report_generation_job_service = ReportGenerationJobService(
            repository=PostgreSQLReportGenerationJobRepository(isolated_database),
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
