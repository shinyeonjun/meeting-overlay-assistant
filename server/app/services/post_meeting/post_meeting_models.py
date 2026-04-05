"""회의 종료 후처리 결과 모델."""

from __future__ import annotations

from dataclasses import dataclass

from server.app.domain.models.session_post_processing_job import (
    SessionPostProcessingJob,
)
from server.app.domain.session import MeetingSession


@dataclass(frozen=True)
class PostMeetingFinalizationResult:
    """세션 종료 후처리 orchestration 결과."""

    session: MeetingSession
    post_processing_job: SessionPostProcessingJob | None
