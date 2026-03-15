"""리포트 생성 후처리 job 모델."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ReportGenerationJob:
    """세션 종료 후 리포트 생성 작업 상태를 보관한다."""

    id: str
    session_id: str
    status: str
    recording_path: str | None
    transcript_path: str | None
    markdown_report_id: str | None
    pdf_report_id: str | None
    error_message: str | None
    requested_by_user_id: str | None
    created_at: str
    started_at: str | None
    completed_at: str | None

    @classmethod
    def create_pending(
        cls,
        *,
        session_id: str,
        recording_path: str | None,
        requested_by_user_id: str | None = None,
    ) -> "ReportGenerationJob":
        """새 리포트 생성 작업을 대기 상태로 만든다."""

        return cls(
            id=f"report-job-{uuid4().hex}",
            session_id=session_id,
            status="pending",
            recording_path=recording_path,
            transcript_path=None,
            markdown_report_id=None,
            pdf_report_id=None,
            error_message=None,
            requested_by_user_id=requested_by_user_id,
            created_at=_utc_now_iso(),
            started_at=None,
            completed_at=None,
        )

    def mark_processing(self) -> "ReportGenerationJob":
        """작업 상태를 처리 중으로 전이한다."""

        return ReportGenerationJob(
            id=self.id,
            session_id=self.session_id,
            status="processing",
            recording_path=self.recording_path,
            transcript_path=self.transcript_path,
            markdown_report_id=self.markdown_report_id,
            pdf_report_id=self.pdf_report_id,
            error_message=None,
            requested_by_user_id=self.requested_by_user_id,
            created_at=self.created_at,
            started_at=_utc_now_iso(),
            completed_at=None,
        )

    def mark_completed(
        self,
        *,
        transcript_path: str | None,
        markdown_report_id: str | None,
        pdf_report_id: str | None,
    ) -> "ReportGenerationJob":
        """작업 상태를 완료로 전이한다."""

        return ReportGenerationJob(
            id=self.id,
            session_id=self.session_id,
            status="completed",
            recording_path=self.recording_path,
            transcript_path=transcript_path,
            markdown_report_id=markdown_report_id,
            pdf_report_id=pdf_report_id,
            error_message=None,
            requested_by_user_id=self.requested_by_user_id,
            created_at=self.created_at,
            started_at=self.started_at or _utc_now_iso(),
            completed_at=_utc_now_iso(),
        )

    def mark_failed(self, error_message: str) -> "ReportGenerationJob":
        """작업 상태를 실패로 전이한다."""

        return ReportGenerationJob(
            id=self.id,
            session_id=self.session_id,
            status="failed",
            recording_path=self.recording_path,
            transcript_path=self.transcript_path,
            markdown_report_id=self.markdown_report_id,
            pdf_report_id=self.pdf_report_id,
            error_message=error_message,
            requested_by_user_id=self.requested_by_user_id,
            created_at=self.created_at,
            started_at=self.started_at or _utc_now_iso(),
            completed_at=_utc_now_iso(),
        )
