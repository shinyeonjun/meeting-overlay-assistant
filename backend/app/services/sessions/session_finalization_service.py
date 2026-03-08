"""세션 종료 후 최종 산출물을 생성하는 orchestration 서비스."""

from __future__ import annotations

from pathlib import Path

from backend.app.core.config import ROOT_DIR
from backend.app.domain.models.session import MeetingSession
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
        self._ensure_final_reports(session_id)
        return session

    def _ensure_final_reports(self, session_id: str) -> None:
        reports = self._report_service.list_reports(session_id)
        existing_types = {report.report_type for report in reports}
        reports_dir = ROOT_DIR / "backend" / "data" / "reports"

        if "markdown" not in existing_types and "pdf" not in existing_types:
            self._report_service.regenerate_reports(
                session_id=session_id,
                output_dir=Path(reports_dir),
            )
            return

        if "markdown" not in existing_types:
            self._report_service.build_markdown_report(
                session_id=session_id,
                output_dir=Path(reports_dir),
            )
        if "pdf" not in existing_types:
            self._report_service.build_pdf_report(
                session_id=session_id,
                output_dir=Path(reports_dir),
            )
