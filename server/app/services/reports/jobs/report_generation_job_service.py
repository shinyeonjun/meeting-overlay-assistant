"""리포트 생성 job 서비스."""

from __future__ import annotations

import logging
from pathlib import Path

from server.app.core.config import ROOT_DIR
from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.repositories.contracts.report_generation_job_repository import (
    ReportGenerationJobRepository,
)
from server.app.services.audio.io.session_recording import find_session_recording_path
from server.app.services.reports.core.report_service import ReportService
from server.app.services.reports.report_models import FinalReportStatus


logger = logging.getLogger(__name__)


class ReportGenerationJobService:
    """세션 종료 후 리포트 생성 job을 관리한다."""

    def __init__(
        self,
        *,
        repository: ReportGenerationJobRepository,
        report_service: ReportService,
        report_knowledge_indexing_service=None,
        output_dir: Path | None = None,
    ) -> None:
        self._repository = repository
        self._report_service = report_service
        self._report_knowledge_indexing_service = report_knowledge_indexing_service
        self._output_dir = output_dir or (ROOT_DIR / "server" / "data" / "reports")

    def enqueue_for_session(
        self,
        *,
        session_id: str,
        requested_by_user_id: str | None = None,
    ) -> ReportGenerationJob:
        """세션 기준 최신 리포트 생성 job을 대기 상태로 만든다."""

        latest_job = self._repository.get_latest_by_session(session_id)
        if latest_job is not None and latest_job.status in {"pending", "processing"}:
            return latest_job

        recording_path = find_session_recording_path(session_id)
        job = ReportGenerationJob.create_pending(
            session_id=session_id,
            recording_path=str(recording_path) if recording_path is not None else None,
            requested_by_user_id=requested_by_user_id,
        )
        return self._repository.save(job)

    def get_latest_job(self, session_id: str) -> ReportGenerationJob | None:
        """세션 기준 최신 리포트 생성 job을 조회한다."""

        return self._repository.get_latest_by_session(session_id)

    def process_latest_pending_for_session(self, session_id: str) -> ReportGenerationJob | None:
        """세션 기준 최신 pending job 하나를 처리한다."""

        latest_job = self._repository.get_latest_by_session(session_id)
        if latest_job is None or latest_job.status != "pending":
            return latest_job
        return self.process_job(latest_job.id)

    def process_job(self, job_id: str) -> ReportGenerationJob:
        """리포트 생성 job을 즉시 처리한다."""

        job = self._repository.get_by_id(job_id)
        if job is None:
            raise ValueError(f"리포트 생성 job을 찾을 수 없습니다: {job_id}")
        if job.status == "completed":
            return job
        if job.status == "processing":
            return job

        processing_job = self._repository.update(job.mark_processing())
        try:
            recording_path = (
                Path(processing_job.recording_path)
                if processing_job.recording_path
                else None
            )
            if recording_path is None or not recording_path.exists():
                failed_job = processing_job.mark_failed("recording_not_found")
                return self._repository.update(failed_job)

            markdown_report, pdf_report = self._report_service.regenerate_reports(
                session_id=processing_job.session_id,
                output_dir=self._output_dir,
                audio_path=recording_path,
                generated_by_user_id=processing_job.requested_by_user_id,
            )
            self._try_index_markdown_report(markdown_report)
            completed_job = processing_job.mark_completed(
                transcript_path=markdown_report.transcript_path,
                markdown_report_id=markdown_report.report.id,
                pdf_report_id=pdf_report.report.id,
            )
            return self._repository.update(completed_job)
        except Exception as error:
            logger.exception(
                "리포트 생성 job 처리 실패: session_id=%s job_id=%s",
                processing_job.session_id,
                processing_job.id,
            )
            failed_job = processing_job.mark_failed(str(error))
            return self._repository.update(failed_job)

    def build_final_status(
        self,
        *,
        session_id: str,
        session_ended: bool,
    ) -> FinalReportStatus:
        """job과 리포트 메타데이터를 합쳐 최종 상태를 계산한다."""

        latest_job = self._repository.get_latest_by_session(session_id)
        if latest_job is None:
            return self._report_service.get_final_status(
                session_id=session_id,
                session_ended=session_ended,
            )

        reports = self._report_service.list_reports(session_id)
        latest_report = reports[-1] if reports else None
        latest_file_path = latest_report.file_path if latest_report is not None else None
        if latest_job.status == "completed":
            if latest_file_path is None:
                status = "failed"
            else:
                latest_path = Path(latest_file_path)
                status = "completed" if latest_path.exists() else "failed"
        else:
            status = latest_job.status

        return FinalReportStatus(
            session_id=session_id,
            status=status,
            report_count=len(reports),
            latest_report_id=latest_report.id if latest_report is not None else None,
            latest_report_type=latest_report.report_type if latest_report is not None else None,
            latest_generated_at=latest_report.generated_at if latest_report is not None else None,
            latest_file_path=latest_report.file_path if latest_report is not None else None,
        )

    def _try_index_markdown_report(self, markdown_report) -> None:
        if self._report_knowledge_indexing_service is None:
            return
        try:
            self._report_knowledge_indexing_service.index_markdown_report(markdown_report)
        except Exception:
            logger.exception(
                "report knowledge 인덱싱 실패: session_id=%s report_id=%s",
                markdown_report.report.session_id,
                markdown_report.report.id,
            )
