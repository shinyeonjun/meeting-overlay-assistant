"""노트 transcript 보정 job 서비스."""

from __future__ import annotations

import logging
from collections.abc import Callable

from server.app.domain.models.note_correction_job import NoteCorrectionJob
from server.app.repositories.contracts.note_correction_job_repository import (
    NoteCorrectionJobRepository,
)
from server.app.repositories.contracts.session import SessionRepository
from server.app.repositories.contracts.utterance_repository import UtteranceRepository
from server.app.services.reports.jobs.helpers.time_utils import (
    utc_after_seconds_iso,
    utc_now_iso,
)
from server.app.services.reports.jobs.note_correction_job_queue import (
    NoteCorrectionJobQueue,
)
from server.app.services.reports.jobs.report_generation_job_service import (
    ReportGenerationJobService,
)
from server.app.services.reports.refinement import (
    NoteTranscriptCorrector,
    TranscriptCorrectionDocument,
    TranscriptCorrectionStore,
)


logger = logging.getLogger(__name__)


class NoteCorrectionJobService:
    """세션 raw transcript를 corrected transcript로 만드는 단계를 관리한다."""

    def __init__(
        self,
        *,
        repository: NoteCorrectionJobRepository,
        session_repository: SessionRepository,
        utterance_repository: UtteranceRepository,
        note_transcript_corrector: (
            NoteTranscriptCorrector | Callable[[], NoteTranscriptCorrector | None] | None
        ) = None,
        transcript_correction_store: TranscriptCorrectionStore | None = None,
        report_generation_job_service: (
            ReportGenerationJobService | Callable[[], ReportGenerationJobService | None] | None
        ) = None,
        job_queue: NoteCorrectionJobQueue | None = None,
    ) -> None:
        self._repository = repository
        self._session_repository = session_repository
        self._utterance_repository = utterance_repository
        self._note_transcript_corrector = (
            None if callable(note_transcript_corrector) else note_transcript_corrector
        )
        self._note_transcript_corrector_factory = (
            note_transcript_corrector if callable(note_transcript_corrector) else None
        )
        self._transcript_correction_store = transcript_correction_store
        self._report_generation_job_service = (
            None if callable(report_generation_job_service) else report_generation_job_service
        )
        self._report_generation_job_service_factory = (
            report_generation_job_service if callable(report_generation_job_service) else None
        )
        self._job_queue = job_queue

    def enqueue_for_session(
        self,
        *,
        session_id: str,
        source_version: int,
        requested_by_user_id: str | None = None,
        dispatch: bool = True,
    ) -> NoteCorrectionJob:
        """세션 기준 최신 pending correction job을 재사용하거나 새로 만든다."""

        session = self._session_repository.get_by_id(session_id)
        if session is None:
            raise ValueError(f"존재하지 않는 세션입니다: {session_id}")

        latest_job = self._repository.get_latest_by_session(session_id)
        if latest_job is not None and latest_job.source_version == source_version:
            if latest_job.status == "processing":
                return latest_job
            if latest_job.status == "pending":
                if dispatch:
                    self.dispatch_job(latest_job.id)
                return latest_job
            if latest_job.status == "completed":
                return latest_job

        job = NoteCorrectionJob.create_pending(
            session_id=session_id,
            source_version=source_version,
            requested_by_user_id=requested_by_user_id,
        )
        saved_job = self._repository.save(job)
        if dispatch:
            self.dispatch_job(saved_job.id)
        return saved_job

    def dispatch_job(self, job_id: str) -> bool:
        """대기 중인 job을 큐에 발행한다."""

        if self._job_queue is None:
            return False
        return self._job_queue.publish(job_id)

    @property
    def has_queue(self) -> bool:
        """노트 보정 job 큐 사용 여부를 반환한다."""

        return self._job_queue is not None

    def wait_for_dispatched_job(self, timeout_seconds: float) -> str | None:
        """큐에서 노트 보정 job 신호를 기다린다."""

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
        """처리 중인 노트 보정 job lease를 연장한다."""

        return self._repository.renew_lease(
            job_id=job_id,
            worker_id=worker_id,
            lease_expires_at=utc_after_seconds_iso(lease_duration_seconds),
        )

    def get_latest_job(self, session_id: str) -> NoteCorrectionJob | None:
        """세션 기준 최신 노트 보정 job을 조회한다."""

        return self._repository.get_latest_by_session(session_id)

    def claim_available_jobs(
        self,
        *,
        worker_id: str,
        lease_duration_seconds: int,
        limit: int = 10,
    ) -> list[NoteCorrectionJob]:
        """pending 또는 lease 만료 job을 claim한다."""

        return self._repository.claim_available(
            worker_id=worker_id,
            lease_expires_at=utc_after_seconds_iso(lease_duration_seconds),
            claimed_at=utc_now_iso(),
            limit=limit,
        )

    def process_available_jobs(
        self,
        *,
        worker_id: str,
        lease_duration_seconds: int,
        limit: int = 10,
    ) -> list[NoteCorrectionJob]:
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

    def process_job(
        self,
        job_id: str,
        *,
        expected_worker_id: str | None = None,
    ) -> NoteCorrectionJob:
        """노트 보정 job 하나를 처리한다."""

        processing_job = self._resolve_processing_job(
            job_id=job_id,
            expected_worker_id=expected_worker_id,
        )
        if processing_job.status == "completed":
            return processing_job

        session = self._session_repository.get_by_id(processing_job.session_id)
        if session is None:
            failed_job = processing_job.mark_failed(
                f"존재하지 않는 세션입니다: {processing_job.session_id}"
            )
            return self._repository.update(failed_job)

        if session.canonical_transcript_version != processing_job.source_version:
            logger.info(
                "note correction job 생략: session_id=%s source_version=%s current_version=%s",
                processing_job.session_id,
                processing_job.source_version,
                session.canonical_transcript_version,
            )
            return self._repository.update(processing_job.mark_completed())

        try:
            document = self._build_correction_document(
                session_id=processing_job.session_id,
                source_version=processing_job.source_version,
            )
            if self._transcript_correction_store is not None:
                self._transcript_correction_store.save(document)

            completed_job = self._repository.update(processing_job.mark_completed())
            report_generation_job_service = self._get_report_generation_job_service()
            if report_generation_job_service is not None:
                report_generation_job_service.enqueue_for_session(
                    session_id=processing_job.session_id,
                    requested_by_user_id=processing_job.requested_by_user_id,
                    dispatch=True,
                )
            return completed_job
        except Exception as error:
            logger.exception(
                "노트 보정 job 처리 실패: session_id=%s job_id=%s worker_id=%s",
                processing_job.session_id,
                processing_job.id,
                expected_worker_id,
            )
            failed_job = processing_job.mark_failed(str(error))
            return self._repository.update(failed_job)

    def _resolve_processing_job(
        self,
        *,
        job_id: str,
        expected_worker_id: str | None,
    ) -> NoteCorrectionJob:
        job = self._repository.get_by_id(job_id)
        if job is None:
            raise ValueError(f"노트 보정 job을 찾을 수 없습니다: {job_id}")
        if job.status == "completed":
            return job

        if expected_worker_id is not None:
            if job.status != "processing":
                raise ValueError(f"claim되지 않은 노트 보정 job입니다: {job_id}")
            if job.claimed_by_worker_id != expected_worker_id:
                raise ValueError(f"다른 worker가 claim한 노트 보정 job입니다: {job_id}")
            return job

        if job.status == "processing":
            return job

        return self._repository.update(
            job.mark_processing(
                started_at=utc_now_iso(),
            )
        )

    def _build_correction_document(
        self,
        *,
        session_id: str,
        source_version: int,
    ) -> TranscriptCorrectionDocument:
        utterances = self._utterance_repository.list_by_session(session_id)
        corrector = self._get_note_transcript_corrector()
        if corrector is None:
            return TranscriptCorrectionDocument(
                session_id=session_id,
                source_version=source_version,
                model="disabled",
                items=[],
            )
        return corrector.correct(
            session_id=session_id,
            source_version=source_version,
            utterances=utterances,
        )

    def _get_note_transcript_corrector(self) -> NoteTranscriptCorrector | None:
        if (
            self._note_transcript_corrector is None
            and self._note_transcript_corrector_factory is not None
        ):
            self._note_transcript_corrector = self._note_transcript_corrector_factory()
        return self._note_transcript_corrector

    def _get_report_generation_job_service(self) -> ReportGenerationJobService | None:
        if (
            self._report_generation_job_service is None
            and self._report_generation_job_service_factory is not None
        ):
            self._report_generation_job_service = (
                self._report_generation_job_service_factory()
            )
        return self._report_generation_job_service
