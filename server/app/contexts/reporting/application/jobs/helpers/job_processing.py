"""리포트 generation job 처리 helper."""

from __future__ import annotations

import logging
from pathlib import Path

from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.repositories.contracts.report_generation_job_repository import (
    ReportGenerationJobRepository,
)
from server.app.contexts.live_capture import resolve_recording_reference
from server.app.contexts.reporting.application.core.report_service import ReportService
from server.app.workers.job_claim_fence import (
    StaleJobClaimError,
    ensure_claim_held,
    is_claim_held,
    write_claimed_job,
)


def try_index_markdown_report(
    *,
    markdown_report,
    report_knowledge_indexing_service,
    logger: logging.Logger,
) -> None:
    """마크다운 리포트 인덱싱을 시도하고 실패는 로그만 남긴다."""

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
    """리포트 generation job 본문 처리 흐름을 실행한다."""

    fence_worker_id = expected_worker_id or processing_job.claimed_by_worker_id
    try:
        # 리포트 파일 생성 전에 claim을 확인한다. 생성 도중 claim이 넘어가는 경우는 막지 못하지만,
        # 그 결과는 아래 완료 쓰기에서 펜싱으로 DB 상태에 반영되지 않는다.
        ensure_claim_held(repository, processing_job, fence_worker_id)
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
        return write_claimed_job(repository, completed_job, fence_worker_id)
    except StaleJobClaimError:
        logger.warning(
            "리포트 생성 job claim을 잃어 결과를 쓰지 않았습니다: job_id=%s worker_id=%s",
            processing_job.id,
            fence_worker_id,
        )
        return repository.get_by_id(processing_job.id) or processing_job
    except Exception as error:
        logger.exception(
            "리포트 생성 job 처리 실패: session_id=%s job_id=%s worker_id=%s",
            processing_job.session_id,
            processing_job.id,
            expected_worker_id,
        )
        if not is_claim_held(repository, processing_job.id, fence_worker_id):
            logger.warning("claim이 넘어가 리포트 실패 기록을 건너뜁니다: job_id=%s", processing_job.id)
            return repository.get_by_id(processing_job.id) or processing_job
        failed_job = processing_job.mark_failed(str(error))
        try:
            return write_claimed_job(repository, failed_job, fence_worker_id)
        except StaleJobClaimError:
            return repository.get_by_id(processing_job.id) or processing_job
