"""서버 재시작 후 post-meeting 파이프라인을 복구하는 서비스."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from server.app.repositories.contracts.session import SessionRepository
from server.app.services.post_meeting.session_post_processing_job_service import (
    SessionPostProcessingJobService,
)
from server.app.services.reports.jobs.note_correction_job_service import (
    NoteCorrectionJobService,
)
from server.app.services.reports.jobs.report_generation_job_service import (
    ReportGenerationJobService,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineRecoverySummary:
    """startup recovery가 다시 큐잉한 단계별 job 수를 요약한다."""

    scanned_sessions: int = 0
    requeued_post_processing_jobs: int = 0
    requeued_note_correction_jobs: int = 0
    requeued_report_jobs: int = 0


class PostMeetingPipelineRecoveryService:
    """startup 시 끊긴 후처리 파이프라인을 다시 큐잉한다.

    세션별 final-status를 기준으로 현재 멈춘 단계를 판별하고,
    아직 끝나지 않은 가장 앞 단계만 다시 큐에 넣는다.
    """

    def __init__(
        self,
        *,
        session_repository: SessionRepository,
        session_post_processing_job_service: SessionPostProcessingJobService,
        note_correction_job_service: NoteCorrectionJobService,
        report_generation_job_service: ReportGenerationJobService,
        max_attempts: int,
    ) -> None:
        self._session_repository = session_repository
        self._session_post_processing_job_service = session_post_processing_job_service
        self._note_correction_job_service = note_correction_job_service
        self._report_generation_job_service = report_generation_job_service
        self._max_attempts = max(max_attempts, 1)

    async def recover_async(self, *, limit: int = 500) -> PipelineRecoverySummary:
        return await asyncio.to_thread(self.recover, limit=limit)

    def recover(self, *, limit: int = 500) -> PipelineRecoverySummary:
        sessions = self._session_repository.list_recent(limit=limit)
        summary = PipelineRecoverySummary(scanned_sessions=len(sessions))

        for session in sessions:
            final_status = self._report_generation_job_service.build_final_status(session=session)
            if final_status.pipeline_stage == "completed":
                continue

            # 단계는 항상 앞에서부터 하나씩만 복구한다.
            # 예를 들어 post_processing이 안 끝났으면 note/report는 건드리지 않는다.
            if final_status.pipeline_stage == "post_processing":
                if self._recover_post_processing(session.id):
                    summary = PipelineRecoverySummary(
                        scanned_sessions=summary.scanned_sessions,
                        requeued_post_processing_jobs=summary.requeued_post_processing_jobs + 1,
                        requeued_note_correction_jobs=summary.requeued_note_correction_jobs,
                        requeued_report_jobs=summary.requeued_report_jobs,
                    )
                continue

            if final_status.pipeline_stage == "note_correction":
                if self._recover_note_correction(
                    session.id,
                    source_version=session.canonical_transcript_version,
                ):
                    summary = PipelineRecoverySummary(
                        scanned_sessions=summary.scanned_sessions,
                        requeued_post_processing_jobs=summary.requeued_post_processing_jobs,
                        requeued_note_correction_jobs=summary.requeued_note_correction_jobs + 1,
                        requeued_report_jobs=summary.requeued_report_jobs,
                    )
                continue

            if final_status.pipeline_stage == "report_generation":
                if self._recover_report_generation(session.id):
                    summary = PipelineRecoverySummary(
                        scanned_sessions=summary.scanned_sessions,
                        requeued_post_processing_jobs=summary.requeued_post_processing_jobs,
                        requeued_note_correction_jobs=summary.requeued_note_correction_jobs,
                        requeued_report_jobs=summary.requeued_report_jobs + 1,
                    )

        if (
            summary.requeued_post_processing_jobs
            or summary.requeued_note_correction_jobs
            or summary.requeued_report_jobs
        ):
            logger.warning(
                "post-meeting 파이프라인 startup recovery 완료: scanned=%s post=%s note=%s report=%s",
                summary.scanned_sessions,
                summary.requeued_post_processing_jobs,
                summary.requeued_note_correction_jobs,
                summary.requeued_report_jobs,
            )
        else:
            logger.info(
                "post-meeting 파이프라인 startup recovery 대상이 없습니다: scanned=%s",
                summary.scanned_sessions,
            )
        return summary

    def _recover_post_processing(self, session_id: str) -> bool:
        latest_job = self._session_post_processing_job_service.get_latest_job(session_id)
        if latest_job is None:
            self._session_post_processing_job_service.enqueue_for_session(
                session_id=session_id,
                requested_by_user_id=None,
                dispatch=True,
            )
            return True

        if latest_job.status == "pending":
            return self._session_post_processing_job_service.dispatch_job(latest_job.id)
        if latest_job.status == "processing" and self._is_job_stalled(latest_job.lease_expires_at):
            return self._session_post_processing_job_service.dispatch_job(latest_job.id)
        if latest_job.status == "failed" and latest_job.attempt_count < self._max_attempts:
            self._session_post_processing_job_service.enqueue_for_session(
                session_id=session_id,
                requested_by_user_id=None,
                dispatch=True,
            )
            return True
        return False

    def _recover_note_correction(self, session_id: str, *, source_version: int) -> bool:
        latest_job = self._note_correction_job_service.get_latest_job(session_id)
        current_job = (
            latest_job
            if latest_job is not None and latest_job.source_version == source_version
            else None
        )

        if current_job is None:
            self._note_correction_job_service.enqueue_for_session(
                session_id=session_id,
                source_version=source_version,
                requested_by_user_id=None,
                dispatch=True,
            )
            return True

        if current_job.status == "pending":
            return self._note_correction_job_service.dispatch_job(current_job.id)
        if current_job.status == "processing" and self._is_job_stalled(current_job.lease_expires_at):
            return self._note_correction_job_service.dispatch_job(current_job.id)
        if current_job.status == "failed" and current_job.attempt_count < self._max_attempts:
            self._note_correction_job_service.enqueue_for_session(
                session_id=session_id,
                source_version=source_version,
                requested_by_user_id=None,
                dispatch=True,
            )
            return True
        return False

    def _recover_report_generation(self, session_id: str) -> bool:
        latest_job = self._report_generation_job_service.get_latest_job(session_id)
        if latest_job is None:
            self._report_generation_job_service.enqueue_for_session(
                session_id=session_id,
                requested_by_user_id=None,
                dispatch=True,
            )
            return True

        if latest_job.status == "pending":
            return self._report_generation_job_service.dispatch_job(latest_job.id)
        if latest_job.status == "processing" and self._is_job_stalled(latest_job.lease_expires_at):
            return self._report_generation_job_service.dispatch_job(latest_job.id)
        if latest_job.status in {"failed", "completed"} and latest_job.attempt_count < self._max_attempts:
            self._report_generation_job_service.enqueue_for_session(
                session_id=session_id,
                requested_by_user_id=None,
                dispatch=True,
            )
            return True
        return False

    @staticmethod
    def _is_job_stalled(lease_expires_at: str | None) -> bool:
        if not lease_expires_at:
            return True
        try:
            lease_dt = datetime.fromisoformat(lease_expires_at)
        except ValueError:
            return True
        return lease_dt <= datetime.now(lease_dt.tzinfo)
