"""공통 영역의 post meeting pipeline service 서비스를 제공한다."""
from __future__ import annotations

from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.services.participation.participant_followup_service import (
    ParticipantFollowupService,
)
from server.app.services.post_meeting.post_meeting_models import (
    PostMeetingFinalizationResult,
)
from server.app.services.post_meeting.session_post_processing_job_service import (
    SessionPostProcessingJobService,
)
from server.app.services.sessions.session_service import SessionService


class PostMeetingPipelineService:
    """세션 종료 후 후처리 준비 단계를 묶어 실행한다."""

    def __init__(
        self,
        *,
        session_service: SessionService,
        participant_followup_service: ParticipantFollowupService,
        session_post_processing_job_service: SessionPostProcessingJobService,
    ) -> None:
        self._session_service = session_service
        self._participant_followup_service = participant_followup_service
        self._session_post_processing_job_service = session_post_processing_job_service

    def finalize_session(
        self,
        session_id: str,
        *,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
        resolved_by_user_id: str | None = None,
        dispatch_post_processing_job: bool = True,
    ) -> PostMeetingFinalizationResult:
        """세션 종료와 후처리 준비를 한 번에 실행한다."""

        ended_session = self._session_service.end_session(session_id)
        self._participant_followup_service.sync_followups_for_session(
            session=ended_session,
            workspace_id=workspace_id,
            resolved_by_user_id=resolved_by_user_id,
        )
        post_processing_job = self._session_post_processing_job_service.enqueue_for_session(
            session_id=ended_session.id,
            requested_by_user_id=resolved_by_user_id,
            dispatch=dispatch_post_processing_job,
        )
        refreshed_session = self._session_service.get_session(ended_session.id) or ended_session
        return PostMeetingFinalizationResult(
            session=refreshed_session,
            post_processing_job=post_processing_job,
        )
