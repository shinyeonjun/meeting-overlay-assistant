"""노트 transcript 보정 job 서비스."""

from __future__ import annotations

import logging
import time
from contextlib import nullcontext
from collections.abc import Callable

from server.app.domain.models.note_correction_job import NoteCorrectionJob
from server.app.repositories.contracts.events.event_repository import (
    MeetingEventRepository,
)
from server.app.repositories.contracts.note_correction_job_repository import (
    NoteCorrectionJobRepository,
)
from server.app.repositories.contracts.session import SessionRepository
from server.app.repositories.contracts.session_post_processing_job_repository import (
    SessionPostProcessingJobRepository,
)
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
from server.app.services.sessions.workspace_summary_store import WorkspaceSummaryStore


logger = logging.getLogger(__name__)


class NoteCorrectionJobService:
    """세션 raw transcript를 corrected transcript로 만드는 단계를 관리한다."""

    def __init__(
        self,
        *,
        repository: NoteCorrectionJobRepository,
        session_repository: SessionRepository,
        utterance_repository: UtteranceRepository,
        event_repository: MeetingEventRepository | None = None,
        note_transcript_corrector: (
            NoteTranscriptCorrector | Callable[[], NoteTranscriptCorrector | None] | None
        ) = None,
        transcript_correction_store: TranscriptCorrectionStore | None = None,
        workspace_summary_synthesizer=None,
        workspace_summary_store: WorkspaceSummaryStore | None = None,
        workspace_summary_knowledge_indexing_service=None,
        session_post_processing_job_repository: (
            SessionPostProcessingJobRepository | None
        ) = None,
        gpu_heavy_execution_gate=None,
        workspace_summary_wait_timeout_seconds: float = 300.0,
        workspace_summary_poll_interval_seconds: float = 5.0,
        gpu_heavy_poll_interval_seconds: float = 1.0,
        report_generation_job_service: (
            ReportGenerationJobService | Callable[[], ReportGenerationJobService | None] | None
        ) = None,
        job_queue: NoteCorrectionJobQueue | None = None,
    ) -> None:
        self._repository = repository
        self._session_repository = session_repository
        self._utterance_repository = utterance_repository
        self._event_repository = event_repository
        self._note_transcript_corrector = (
            None if callable(note_transcript_corrector) else note_transcript_corrector
        )
        self._note_transcript_corrector_factory = (
            note_transcript_corrector if callable(note_transcript_corrector) else None
        )
        self._transcript_correction_store = transcript_correction_store
        self._workspace_summary_synthesizer = (
            None if callable(workspace_summary_synthesizer) else workspace_summary_synthesizer
        )
        self._workspace_summary_synthesizer_factory = (
            workspace_summary_synthesizer
            if callable(workspace_summary_synthesizer)
            else None
        )
        self._workspace_summary_store = workspace_summary_store
        self._workspace_summary_knowledge_indexing_service = (
            workspace_summary_knowledge_indexing_service
        )
        self._session_post_processing_job_repository = (
            session_post_processing_job_repository
        )
        self._gpu_heavy_execution_gate = gpu_heavy_execution_gate
        self._workspace_summary_wait_timeout_seconds = max(
            workspace_summary_wait_timeout_seconds,
            0.0,
        )
        self._workspace_summary_poll_interval_seconds = max(
            workspace_summary_poll_interval_seconds,
            0.1,
        )
        self._gpu_heavy_poll_interval_seconds = max(
            gpu_heavy_poll_interval_seconds,
            0.1,
        )
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

        if self._should_defer_claim_for_live_sessions(worker_id=worker_id):
            return []

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
            self._maybe_save_workspace_summary(
                session=session,
                source_version=processing_job.source_version,
                utterances=self._utterance_repository.list_by_session(processing_job.session_id),
                correction_document=document,
            )

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

    def _get_workspace_summary_synthesizer(self):
        if (
            self._workspace_summary_synthesizer is None
            and self._workspace_summary_synthesizer_factory is not None
        ):
            self._workspace_summary_synthesizer = (
                self._workspace_summary_synthesizer_factory()
            )
        return self._workspace_summary_synthesizer

    def _should_defer_claim_for_live_sessions(self, *, worker_id: str) -> bool:
        if not self._has_deferred_heavy_work():
            return False

        running_session_count = self._session_repository.count_running()
        if running_session_count <= 0:
            return False

        logger.info(
            "note correction job claim 보류: worker_id=%s running_session_count=%s",
            worker_id,
            running_session_count,
        )
        return True

    def _has_deferred_heavy_work(self) -> bool:
        if (
            self._note_transcript_corrector is not None
            or self._note_transcript_corrector_factory is not None
        ):
            return True
        return self._workspace_summary_store is not None and (
            self._workspace_summary_synthesizer is not None
            or self._workspace_summary_synthesizer_factory is not None
        )

    def _maybe_save_workspace_summary(
        self,
        *,
        session,
        source_version: int,
        utterances,
        correction_document: TranscriptCorrectionDocument | None,
    ) -> None:
        if self._workspace_summary_store is None:
            return

        synthesizer = self._get_workspace_summary_synthesizer()
        if synthesizer is None:
            return

        try:
            with self._hold_workspace_summary_execution_slot(
                session_id=session.id,
                source_version=source_version,
            ):
                events = (
                    self._event_repository.list_by_session(session.id)
                    if self._event_repository is not None
                    else []
                )
                summary_document = synthesizer.synthesize(
                    session=session,
                    source_version=source_version,
                    utterances=utterances,
                    correction_document=correction_document,
                    events=events,
                )
                if summary_document is None:
                    return
                self._workspace_summary_store.save(summary_document)
                self._try_index_workspace_summary(summary_document)
        except Exception:
            logger.exception(
                "workspace summary 저장 실패: session_id=%s source_version=%s",
                session.id,
                source_version,
            )

    def _try_index_workspace_summary(self, summary_document) -> None:
        service = self._workspace_summary_knowledge_indexing_service
        if service is None:
            return
        try:
            service.index_workspace_summary(summary_document)
        except Exception:
            logger.exception(
                "workspace summary knowledge 인덱싱 실패: session_id=%s source_version=%s",
                summary_document.session_id,
                summary_document.source_version,
            )

    def _hold_workspace_summary_execution_slot(
        self,
        *,
        session_id: str,
        source_version: int,
    ):
        self._wait_for_running_sessions_quiet_period(session_id=session_id)
        gate = self._gpu_heavy_execution_gate
        if gate is None:
            self._wait_for_post_processing_quiet_period(session_id=session_id)
            return nullcontext()
        return gate.hold(
            owner=f"workspace_summary:{session_id}:{source_version}",
            poll_interval_seconds=self._gpu_heavy_poll_interval_seconds,
        )

    def _wait_for_running_sessions_quiet_period(self, *, session_id: str) -> None:
        running_session_count = self._session_repository.count_running()
        if running_session_count <= 0:
            return

        deadline = time.monotonic() + self._workspace_summary_wait_timeout_seconds
        logger.info(
            "workspace summary live 대기 시작: session_id=%s timeout_seconds=%.1f poll_seconds=%.1f running_session_count=%s",
            session_id,
            self._workspace_summary_wait_timeout_seconds,
            self._workspace_summary_poll_interval_seconds,
            running_session_count,
        )

        while running_session_count > 0:
            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0:
                logger.warning(
                    "workspace summary live 대기 시간 초과, 기존 흐름으로 진행: session_id=%s timeout_seconds=%.1f running_session_count=%s",
                    session_id,
                    self._workspace_summary_wait_timeout_seconds,
                    running_session_count,
                )
                return
            time.sleep(min(self._workspace_summary_poll_interval_seconds, remaining_seconds))
            running_session_count = self._session_repository.count_running()

        waited_seconds = max(
            self._workspace_summary_wait_timeout_seconds
            - max(deadline - time.monotonic(), 0.0),
            0.0,
        )
        logger.info(
            "workspace summary live 대기 종료: session_id=%s waited_seconds=%.3f",
            session_id,
            waited_seconds,
        )

    def _wait_for_post_processing_quiet_period(self, *, session_id: str) -> None:
        repository = self._session_post_processing_job_repository
        if repository is None:
            return

        if not repository.has_active_processing_jobs(excluding_session_id=session_id):
            return

        deadline = time.monotonic() + self._workspace_summary_wait_timeout_seconds
        logger.info(
            "workspace summary 대기 시작: session_id=%s timeout_seconds=%.1f poll_seconds=%.1f",
            session_id,
            self._workspace_summary_wait_timeout_seconds,
            self._workspace_summary_poll_interval_seconds,
        )

        while repository.has_active_processing_jobs(excluding_session_id=session_id):
            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0:
                logger.warning(
                    "workspace summary 대기 시간 초과, 기존 흐름으로 진행: session_id=%s timeout_seconds=%.1f",
                    session_id,
                    self._workspace_summary_wait_timeout_seconds,
                )
                return
            time.sleep(min(self._workspace_summary_poll_interval_seconds, remaining_seconds))

        waited_seconds = max(
            self._workspace_summary_wait_timeout_seconds
            - max(deadline - time.monotonic(), 0.0),
            0.0,
        )
        logger.info(
            "workspace summary 대기 종료: session_id=%s waited_seconds=%.3f",
            session_id,
            waited_seconds,
        )
