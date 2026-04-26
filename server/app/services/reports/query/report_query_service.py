"""회의록 조회 전용 서비스"""

from __future__ import annotations

from pathlib import Path

from server.app.domain.models.report import Report
from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.repositories.contracts.report_repository import ReportRepository
from server.app.services.reports.report_models import FinalReportStatus, SessionReportSummary


class ReportQueryService:
    """회의록 조회와 상태 계산만 담당한다."""

    def __init__(
        self,
        report_repository: ReportRepository,
        artifact_store: LocalArtifactStore | None = None,
    ) -> None:
        self._report_repository = report_repository
        self._artifact_store = artifact_store

    def list_reports(self, session_id: str) -> list[Report]:
        """세션 회의록 목록을 반환한다."""

        return self._report_repository.list_by_session(session_id)

    def get_latest_report(self, session_id: str) -> Report | None:
        """세션의 최신 회의록을 반환한다."""

        summary = self.get_session_report_summary(session_id)
        return summary.latest_report

    def get_report_by_id(self, report_id: str) -> Report | None:
        """ID 기준 회의록을 조회한다."""

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
        """최신 회의록 목록을 조회한다."""

        return self._report_repository.list_recent(
            generated_by_user_id=generated_by_user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            limit=limit,
        )

    def count_recent_reports(
        self,
        *,
        generated_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
    ) -> int:
        """최신 회의록 목록 조건과 같은 기준으로 전체 개수를 센다."""

        return self._report_repository.count_recent(
            generated_by_user_id=generated_by_user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
        )

    def get_session_report_summaries(
        self,
        session_ids: list[str],
    ) -> dict[str, SessionReportSummary]:
        """세션별 회의록 개수와 최신 회의록을 한 번에 조회한다."""

        return self._report_repository.get_session_summaries(session_ids)

    def get_session_report_summary(self, session_id: str) -> SessionReportSummary:
        """단일 세션 요약도 bulk 조회 경로를 재사용한다."""

        return self.get_session_report_summaries([session_id]).get(
            session_id,
            SessionReportSummary(session_id=session_id, report_count=0),
        )

    def get_final_status(self, *, session_id: str, session_ended: bool) -> FinalReportStatus:
        """세션 기준 최종 문서 생성 상태를 계산한다."""

        summary = self.get_session_report_summary(session_id)
        latest = summary.latest_report
        if latest is None:
            return FinalReportStatus(
                session_id=session_id,
                status="ready" if session_ended else "pending",
                report_count=0,
            )

        latest_path = self.resolve_report_path(latest)
        return FinalReportStatus(
            session_id=session_id,
            status="completed" if latest_path.exists() else "failed",
            report_count=summary.report_count,
            latest_report_id=latest.id,
            latest_report_type=latest.report_type,
            latest_generated_at=latest.generated_at,
            latest_file_artifact_id=latest.file_artifact_id,
            latest_file_path=latest.file_path,
        )

    def read_report_content(self, report: Report) -> str | None:
        """회의록 본문을 반환한다."""

        if report.report_type != "markdown":
            return None
        report_path = self.resolve_report_path(report)
        if not report_path.exists():
            return None
        return report_path.read_text(encoding="utf-8")

    def report_exists(self, report: Report) -> bool:
        """회의록 파일의 실제 존재 여부를 반환한다."""

        return self.resolve_report_path(report).exists()

    def resolve_report_path(self, report: Report) -> Path:
        """artifact id 또는 fallback path로 회의록 파일 경로를 해석한다."""

        if self._artifact_store is not None:
            resolved_path = self._artifact_store.resolve_path_or_none(
                report.file_artifact_id,
                fallback_path=report.file_path,
            )
            if resolved_path is not None:
                return resolved_path
        return Path(report.file_path)
