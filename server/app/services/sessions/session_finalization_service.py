"""세션 종료 서비스 호환 shim."""

from __future__ import annotations

from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.session import MeetingSession
from server.app.services.participation.participant_followup_service import (
    ParticipantFollowupService,
)
from server.app.services.post_meeting.post_meeting_pipeline_service import (
    PostMeetingPipelineService,
)
from server.app.services.post_meeting.session_post_processing_job_service import (
    SessionPostProcessingJobService,
)
from server.app.services.sessions.session_service import SessionService


class SessionFinalizationService:
    """기존 세션 종료 호출을 위한 호환 wrapper."""

    def __init__(
        self,
        session_service: SessionService,
        session_post_processing_job_service: SessionPostProcessingJobService,
        participant_followup_service: ParticipantFollowupService,
    ) -> None:
        self._pipeline_service = PostMeetingPipelineService(
            session_service=session_service,
            participant_followup_service=participant_followup_service,
            session_post_processing_job_service=session_post_processing_job_service,
        )

    def finalize_session(
        self,
        session_id: str,
        *,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
        resolved_by_user_id: str | None = None,
    ) -> MeetingSession:
        """세션을 종료하고 후처리 준비까지만 수행한다."""

        result = self._pipeline_service.finalize_session(
            session_id,
            workspace_id=workspace_id,
            resolved_by_user_id=resolved_by_user_id,
            dispatch_post_processing_job=False,
        )
        return result.session
