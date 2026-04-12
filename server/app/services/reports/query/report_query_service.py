"""리포트 조회 전용 서비스."""

from __future__ import annotations

from pathlib import Path

from server.app.domain.models.report import Report
from server.app.repositories.contracts.report_repository import ReportRepository
from server.app.services.reports.report_models import FinalReportStatus


class ReportQueryService:
    """리포트 조회와 상태 계산만 담당한다."""

    def __init__(self, report_repository: ReportRepository) -> None:
        self._report_repository = report_repository

    def list_reports(self, session_id: str) -> list[Report]:
        """세션 리포트 목록을 반환한다."""

        return self._report_repository.list_by_session(session_id)

    def get_latest_report(self, session_id: str) -> Report | None:
        """세션의 최신 리포트를 반환한다."""

        reports = self._report_repository.list_by_session(session_id)
        if not reports:
            return None
        return reports[-1]

    def get_report_by_id(self, report_id: str) -> Report | None:
        """ID 기준 리포트를 조회한다."""

        return self._report_repository.get_by_id(report_id)

    def list_recent_reports(
        self,
        *,
        generated_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int | None = 50,
    ) -> list[Report]:
        """최신 리포트 목록을 조회한다."""

        return self._report_repository.list_recent(
            generated_by_user_id=generated_by_user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            limit=limit,
        )

    def get_final_status(self, *, session_id: str, session_ended: bool) -> FinalReportStatus:
        """세션 기준 최종 문서 생성 상태를 계산한다."""

        reports = self._report_repository.list_by_session(session_id)
        report_count = len(reports)
        if report_count == 0:
            return FinalReportStatus(
                session_id=session_id,
                status="processing" if session_ended else "pending",
                report_count=0,
            )

        latest = reports[-1]
        latest_path = Path(latest.file_path)
        return FinalReportStatus(
            session_id=session_id,
            status="completed" if latest_path.exists() else "failed",
            report_count=report_count,
            latest_report_id=latest.id,
            latest_report_type=latest.report_type,
            latest_generated_at=latest.generated_at,
            latest_file_path=latest.file_path,
        )

    @staticmethod
    def read_report_content(report: Report) -> str | None:
        """리포트 본문을 반환한다."""

        if report.report_type != "markdown":
            return None
        report_path = Path(report.file_path)
        if not report_path.exists():
            return None
        return report_path.read_text(encoding="utf-8")
