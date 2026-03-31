"""회의 종료 후 후처리 orchestration 서비스."""

from __future__ import annotations

from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.services.participation.participant_followup_service import (
    ParticipantFollowupService,
)
from server.app.services.post_meeting.post_meeting_models import (
    PostMeetingFinalizationResult,
)
from server.app.services.reports.jobs.report_generation_job_service import (
    ReportGenerationJobService,
)
from server.app.services.sessions.session_service import SessionService


class PostMeetingPipelineService:
    """세션 종료 이후 후처리 단계를 묶어서 실행한다."""

    def __init__(
        self,
        *,
        session_service: SessionService,
        participant_followup_service: ParticipantFollowupService,
        report_generation_job_service: ReportGenerationJobService,
    ) -> None:
        self._session_service = session_service
        self._participant_followup_service = participant_followup_service
        self._report_generation_job_service = report_generation_job_service

    def finalize_session(
        self,
        session_id: str,
        *,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
        resolved_by_user_id: str | None = None,
        create_report_job: bool = False,
        dispatch_report_job: bool = True,
    ) -> PostMeetingFinalizationResult:
        """세션 종료와 직후 후처리 준비를 한 번에 수행한다."""

        ended_session = self._session_service.end_session(session_id)
        self._participant_followup_service.sync_followups_for_session(
            session=ended_session,
            workspace_id=workspace_id,
            resolved_by_user_id=resolved_by_user_id,
        )
        report_generation_job = None
        if create_report_job:
            report_generation_job = self._report_generation_job_service.enqueue_for_session(
                session_id=ended_session.id,
                requested_by_user_id=resolved_by_user_id,
                dispatch=dispatch_report_job,
            )
        return PostMeetingFinalizationResult(
            session=ended_session,
            report_generation_job=report_generation_job,
        )

    def process_report_generation_job(self, job_id: str) -> ReportGenerationJob:
        """리포트 생성 job 하나를 처리한다."""

        return self._report_generation_job_service.process_job(job_id)

    def process_latest_report_job_for_session(
        self,
        session_id: str,
    ) -> ReportGenerationJob | None:
        """세션 기준 최신 pending 리포트 생성 job을 처리한다."""

        return self._report_generation_job_service.process_latest_pending_for_session(
            session_id
        )
