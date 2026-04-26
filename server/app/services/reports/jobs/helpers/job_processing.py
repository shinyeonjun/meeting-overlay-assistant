"""회의록 generation job 처리 helper."""

from __future__ import annotations

import logging
from pathlib import Path

from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.repositories.contracts.report_generation_job_repository import (
    ReportGenerationJobRepository,
)
from server.app.services.audio.io.session_recording import resolve_recording_reference
from server.app.services.reports.core.report_service import ReportService


def try_index_markdown_report(
    *,
    markdown_report,
    report_knowledge_indexing_service,
    logger: logging.Logger,
) -> None:
    """마크다운 회의록 인덱싱을 시도하고 실패는 로그만 남긴다."""

    if report_knowledge_indexing_service is None:
        return
    try:
        report_knowledge_indexing_service.index_markdown_report(markdown_report)
    except Exception:
        logger.exception(
            "report knowledge 인덱싱 실패: session_id=%s report_id=%s",
            markdown_report.report.session_id,
            markdown_report.report.id,
        )


def process_report_generation_job(
    *,
    processing_job: ReportGenerationJob,
    expected_worker_id: str | None,
    repository: ReportGenerationJobRepository,
    report_service: ReportService,
    report_knowledge_indexing_service,
    artifact_store: LocalArtifactStore,
    output_dir: Path,
    logger: logging.Logger,
) -> ReportGenerationJob:
    """회의록 generation job 본문 처리 흐름을 실행한다."""

    try:
        recording_path = resolve_recording_reference(
            artifact_id=processing_job.recording_artifact_id,
            fallback_path=processing_job.recording_path,
            artifact_store=artifact_store,
        )
        markdown_report, pdf_report = report_service.regenerate_reports(
            session_id=processing_job.session_id,
            output_dir=output_dir,
            audio_path=recording_path,
            generated_by_user_id=processing_job.requested_by_user_id,
        )
        try_index_markdown_report(
            markdown_report=markdown_report,
            report_knowledge_indexing_service=report_knowledge_indexing_service,
            logger=logger,
        )
        completed_job = processing_job.mark_completed(
            transcript_path=markdown_report.transcript_path,
            markdown_report_id=markdown_report.report.id,
            pdf_report_id=pdf_report.report.id,
        )
        return repository.update(completed_job)
    except Exception as error:
        logger.exception(
            "회의록 생성 job 처리 실패: session_id=%s job_id=%s worker_id=%s",
            processing_job.session_id,
            processing_job.id,
            expected_worker_id,
        )
        failed_job = processing_job.mark_failed(str(error))
        return repository.update(failed_job)
