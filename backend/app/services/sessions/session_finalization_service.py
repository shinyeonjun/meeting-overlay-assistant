"""세션 종료와 최종 산출물 생성을 담당하는 orchestration 서비스."""

from __future__ import annotations

from pathlib import Path

from backend.app.core.config import ROOT_DIR
from backend.app.domain.models.session import MeetingSession
from backend.app.services.audio.io.session_recording import find_session_recording_path
from backend.app.services.reports.core.report_service import ReportService
from backend.app.services.sessions.session_service import SessionService


class SessionFinalizationService:
    """세션 종료와 최종 리포트 생성을 함께 처리한다."""

    def __init__(
        self,
        session_service: SessionService,
        report_service: ReportService,
    ) -> None:
        self._session_service = session_service
        self._report_service = report_service

    def finalize_session(self, session_id: str) -> MeetingSession:
        """세션을 종료하고 최종 Markdown/PDF 리포트를 생성한다."""

        session = self._session_service.end_session(session_id)
        recording_path = find_session_recording_path(session_id)
        try:
            self._ensure_final_reports(session_id, recording_path=recording_path)
        finally:
            if recording_path is not None:
                recording_path.unlink(missing_ok=True)
        return session

    def _ensure_final_reports(self, session_id: str, recording_path: Path | None = None) -> None:
        reports = self._report_service.list_reports(session_id)
        existing_types = {report.report_type for report in reports}
        reports_dir = ROOT_DIR / "backend" / "data" / "reports"

        if "markdown" not in existing_types and "pdf" not in existing_types:
            self._report_service.regenerate_reports(
                session_id=session_id,
                output_dir=Path(reports_dir),
                audio_path=recording_path,
            )
            return

        if "markdown" not in existing_types:
            self._report_service.build_markdown_report(
                session_id=session_id,
                output_dir=Path(reports_dir),
                audio_path=recording_path,
            )
        if "pdf" not in existing_types:
            self._report_service.build_pdf_report(
                session_id=session_id,
                output_dir=Path(reports_dir),
                audio_path=recording_path,
            )
