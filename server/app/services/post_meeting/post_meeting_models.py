"""공통 영역의 post meeting models 서비스를 제공한다."""
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
