"""리포트 영역의 report generation job service 서비스를 제공한다."""
from __future__ import annotations

import logging
from pathlib import Path

from server.app.core.config import ROOT_DIR, settings
from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.repositories.contracts.session_post_processing_job_repository import (
    SessionPostProcessingJobRepository,
)
from server.app.repositories.contracts.note_correction_job_repository import (
    NoteCorrectionJobRepository,
)
from server.app.repositories.contracts.report_generation_job_repository import (
    ReportGenerationJobRepository,
)
from server.app.services.reports.core.report_service import ReportService
from server.app.services.reports.jobs.helpers.final_status import (
    build_final_report_status,
)
from server.app.services.reports.jobs.helpers.job_lifecycle import (
    claim_jobs_for_worker,
    enqueue_or_reuse_job,
    resolve_processing_job,
)
from server.app.services.reports.jobs.helpers.job_processing import (
    process_report_generation_job,
    try_index_markdown_report,
)
from server.app.services.reports.jobs.report_generation_job_queue import (
    ReportGenerationJobQueue,
)
from server.app.services.reports.report_models import FinalReportStatus, SessionReportSummary


logger = logging.getLogger(__name__)


class ReportGenerationJobService:
    """세션 종료 뒤 리포트 생성 job을 관리한다."""

    def __init__(
        self,
        *,
        repository: ReportGenerationJobRepository,
        session_post_processing_job_repository: SessionPostProcessingJobRepository,
        note_correction_job_repository: NoteCorrectionJobRepository,
        report_service: ReportService,
        report_knowledge_indexing_service=None,
        job_queue: ReportGenerationJobQueue | None = None,
        artifact_store: LocalArtifactStore | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self._repository = repository
        self._session_post_processing_job_repository = session_post_processing_job_repository
        self._note_correction_job_repository = note_correction_job_repository
        self._report_service = report_service
        self._report_knowledge_indexing_service = report_knowledge_indexing_service
        self._job_queue = job_queue
        self._artifact_store = artifact_store or LocalArtifactStore(settings.artifacts_root_path)
        self._output_dir = output_dir or (ROOT_DIR / "server" / "data" / "reports")

    def enqueue_for_session(
        self,
        *,
        session_id: str,
        requested_by_user_id: str | None = None,
        dispatch: bool = True,
    ) -> ReportGenerationJob:
        """세션 기준 최신 리포트 생성 job을 만들거나 재사용한다."""

        return enqueue_or_reuse_job(
            session_id=session_id,
            requested_by_user_id=requested_by_user_id,
            dispatch=dispatch,
            repository=self._repository,
            artifact_store=self._artifact_store,
            dispatch_job=self.dispatch_job,
        )

    def dispatch_job(self, job_id: str) -> bool:
        """대기 중인 job을 큐에 발행한다."""

        if self._job_queue is None:
            return False
        return self._job_queue.publish(job_id)

    @property
    def has_queue(self) -> bool:
        """리포트 생성 job 큐 사용 여부를 반환한다."""

        return self._job_queue is not None

    def wait_for_dispatched_job(self, timeout_seconds: float) -> str | None:
        """큐에서 job 신호를 기다린다."""

        if self._job_queue is None:
            return None
        return self._job_queue.wait_for_job(timeout_seconds)

    def renew_job_lease(
        self,
        *,
        job_id: str,
        worker_id: str,
        lease_duration_seconds: int,
    ) -> bool:
        """처리 중인 report generation job lease를 연장한다."""

        return self._repository.renew_lease(
            job_id=job_id,
            worker_id=worker_id,
            lease_expires_at=utc_after_seconds_iso(lease_duration_seconds),
        )

    def get_latest_job(self, session_id: str) -> ReportGenerationJob | None:
        """세션 기준 최신 리포트 생성 job을 조회한다."""

        return self._repository.get_latest_by_session(session_id)

    def list_pending_jobs(self, limit: int = 10) -> list[ReportGenerationJob]:
        """처리 대기 중인 report generation job 목록을 반환한다."""

        return self._repository.list_pending(limit=limit)

    def claim_available_jobs(
        self,
        *,
        worker_id: str,
        lease_duration_seconds: int,
        limit: int = 10,
    ) -> list[ReportGenerationJob]:
        """pending 또는 lease 만료 job을 worker가 claim한다."""

        return claim_jobs_for_worker(
            repository=self._repository,
            worker_id=worker_id,
            lease_duration_seconds=lease_duration_seconds,
            limit=limit,
        )

    def process_latest_pending_for_session(self, session_id: str) -> ReportGenerationJob | None:
        """세션 기준 최신 pending job 하나를 처리한다."""

        latest_job = self._repository.get_latest_by_session(session_id)
        if latest_job is None or latest_job.status != "pending":
            return latest_job
        return self.process_job(latest_job.id)

    def process_job(
        self,
        job_id: str,
        *,
        expected_worker_id: str | None = None,
    ) -> ReportGenerationJob:
        """리포트 생성 job을 처리한다."""

        processing_job = resolve_processing_job(
            job_id=job_id,
            expected_worker_id=expected_worker_id,
            repository=self._repository,
        )
        if processing_job.status == "completed":
            return processing_job

        return process_report_generation_job(
            processing_job=processing_job,
            expected_worker_id=expected_worker_id,
            repository=self._repository,
            report_service=self._report_service,
            report_knowledge_indexing_service=self._report_knowledge_indexing_service,
            artifact_store=self._artifact_store,
            output_dir=self._output_dir,
            logger=logger,
        )

    def process_available_jobs(
        self,
        *,
        worker_id: str,
        lease_duration_seconds: int,
        limit: int = 10,
    ) -> list[ReportGenerationJob]:
        """worker가 claim 가능한 job을 가져와 순서대로 처리한다."""

        claimed_jobs = self.claim_available_jobs(
            worker_id=worker_id,
            lease_duration_seconds=lease_duration_seconds,
            limit=limit,
        )
        return [
            self.process_job(job.id, expected_worker_id=worker_id)
            for job in claimed_jobs
        ]

    def build_final_status(
        self,
        *,
        session,
    ) -> FinalReportStatus:
        """후처리와 리포트 생성 상태를 합쳐 세션 최종 상태를 계산한다."""

        return self.build_final_statuses({session.id: session})[session.id]

    def build_final_statuses(
        self,
        sessions_by_id: dict[str, object],
    ) -> dict[str, FinalReportStatus]:
        """여러 세션의 리포트 파이프라인 상태를 한 번에 계산한다."""

        if not sessions_by_id:
            return {}

        session_ids = list(sessions_by_id)
        latest_jobs = self._repository.get_latest_by_sessions(session_ids)
        latest_post_processing_jobs = (
            self._session_post_processing_job_repository.get_latest_by_sessions(session_ids)
        )
        latest_note_correction_jobs = self._note_correction_job_repository.get_latest_by_sessions(
            session_ids
        )
        report_summaries = self._report_service.get_session_report_summaries(session_ids)

        return {
            session_id: build_final_report_status(
                session_id=session_id,
                session_ended=getattr(sessions_by_id[session_id], "ended_at", None) is not None,
                post_processing_status=(
                    getattr(sessions_by_id[session_id], "post_processing_status", None)
                    or "not_started"
                ),
                post_processing_job=latest_post_processing_jobs.get(session_id),
                post_processing_error_message=getattr(
                    sessions_by_id[session_id],
                    "post_processing_error_message",
                    None,
                ),
                canonical_transcript_version=getattr(
                    sessions_by_id[session_id],
                    "canonical_transcript_version",
                    0,
                ),
                note_correction_job=latest_note_correction_jobs.get(session_id),
                latest_job=latest_jobs.get(session_id),
                report_summary=report_summaries.get(
                    session_id,
                    SessionReportSummary(session_id=session_id, report_count=0),
                ),
                report_exists=self._report_service.report_exists,
            )
            for session_id in session_ids
        }

    def _try_index_markdown_report(self, markdown_report) -> None:
        """기존 테스트 호환성을 위한 wrapper."""

        try_index_markdown_report(
            markdown_report=markdown_report,
            report_knowledge_indexing_service=self._report_knowledge_indexing_service,
            logger=logger,
        )
