"""회의 종료 후처리 결과 모델."""

from __future__ import annotations

from dataclasses import dataclass

from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.domain.session import MeetingSession


@dataclass(frozen=True)
class PostMeetingFinalizationResult:
    """세션 종료 후처리 orchestration 결과."""

    session: MeetingSession
    report_generation_job: ReportGenerationJob | None
