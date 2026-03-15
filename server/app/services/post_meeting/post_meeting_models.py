"""회의 종료 후 후처리 결과 모델."""

from __future__ import annotations

from dataclasses import dataclass

from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.domain.session import MeetingSession


@dataclass(frozen=True)
class PostMeetingFinalizationResult:
    """세션 종료 후 후처리 orchestration 결과."""

    session: MeetingSession
    report_generation_job: ReportGenerationJob | None

    @property
    def should_process_report_job(self) -> bool:
        """백그라운드 리포트 후처리를 바로 시작할 수 있는지 반환한다."""

        if self.report_generation_job is None:
            return False
        return (
            self.report_generation_job.status == "pending"
            and bool(self.report_generation_job.recording_path)
        )
