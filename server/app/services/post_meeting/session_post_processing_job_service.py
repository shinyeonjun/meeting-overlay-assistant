"""세션 후처리 job 서비스."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from time import time

from server.app.core.config import settings
from server.app.domain.events import MeetingEvent
from server.app.domain.models.session_post_processing_job import SessionPostProcessingJob
from server.app.domain.models.utterance import Utterance
from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.repositories.contracts.events.event_repository import (
    MeetingEventRepository,
)
from server.app.repositories.contracts.session import SessionRepository
from server.app.repositories.contracts.session_post_processing_job_repository import (
    SessionPostProcessingJobRepository,
)
from server.app.repositories.contracts.utterance_repository import UtteranceRepository
from server.app.services.analysis.analyzers.analyzer import MeetingAnalyzer
from server.app.services.audio.io.session_recording import (
    find_session_recording_artifact,
    resolve_recording_reference,
)
from server.app.services.events.meeting_event_service import MeetingEventService
from server.app.services.post_meeting.session_post_processing_job_queue import (
    SessionPostProcessingJobQueue,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    AudioPostprocessingService,
)
from server.app.services.reports.jobs.helpers.time_utils import (
    utc_after_seconds_iso,
    utc_now_iso,
)
from server.app.services.reports.jobs.report_generation_job_service import (
    ReportGenerationJobService,
)


logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(time() * 1000)


class SessionPostProcessingJobService:
    """원본 오디오를 기반으로 canonical transcript/event를 생성한다."""

    def __init__(
        self,
        *,
        repository: SessionPostProcessingJobRepository,
        session_repository: SessionRepository,
        utterance_repository: UtteranceRepository | None = None,
        event_repository: MeetingEventRepository | None = None,
        audio_postprocessing_service: (
            AudioPostprocessingService | Callable[[], AudioPostprocessingService] | None
        ) = None,
        analyzer: MeetingAnalyzer | Callable[[], MeetingAnalyzer] | None = None,
        report_generation_job_service: (
            ReportGenerationJobService | Callable[[], ReportGenerationJobService] | None
        ) = None,
        job_queue: SessionPostProcessingJobQueue | None = None,
        artifact_store: LocalArtifactStore | None = None,
    ) -> None:
        self._repository = repository
        self._session_repository = session_repository
        self._utterance_repository = utterance_repository
        self._event_repository = event_repository
        self._audio_postprocessing_service = (
            None if callable(audio_postprocessing_service) else audio_postprocessing_service
        )
        self._audio_postprocessing_service_factory = (
            audio_postprocessing_service if callable(audio_postprocessing_service) else None
        )
        self._analyzer = None if callable(analyzer) else analyzer
        self._analyzer_factory = analyzer if callable(analyzer) else None
        self._report_generation_job_service = (
            None if callable(report_generation_job_service) else report_generation_job_service
        )
        self._report_generation_job_service_factory = (
            report_generation_job_service if callable(report_generation_job_service) else None
        )
        self._job_queue = job_queue
        self._artifact_store = artifact_store or LocalArtifactStore(settings.artifacts_root_path)
        self._event_service = (
            MeetingEventService(event_repository)
            if event_repository is not None
            else None
        )

    def enqueue_for_session(
        self,
        *,
        session_id: str,
        requested_by_user_id: str | None = None,
        dispatch: bool = True,
    ) -> SessionPostProcessingJob:
        """세션 기준 최신 pending job을 재사용하거나 새로 만든다."""

        session = self._session_repository.get_by_id(session_id)
        if session is None:
            raise ValueError(f"존재하지 않는 세션입니다: {session_id}")

        latest_job = self._repository.get_latest_by_session(session_id)
        if latest_job is not None and latest_job.status in {"pending", "processing"}:
            self._session_repository.save(
                session.queue_post_processing(
                    recording_artifact_id=latest_job.recording_artifact_id,
                )
            )
            if dispatch and latest_job.status == "pending":
                self.dispatch_job(latest_job.id)
            return latest_job

        recording_artifact = self._resolve_recording_artifact(session_id)
        queued_session = session.queue_post_processing(
            recording_artifact_id=(
                recording_artifact.artifact_id if recording_artifact is not None else None
            ),
        )
        self._session_repository.save(queued_session)

        job = SessionPostProcessingJob.create_pending(
            session_id=session_id,
            recording_artifact_id=queued_session.recording_artifact_id,
            recording_path=(
                str(recording_artifact.file_path) if recording_artifact is not None else None
            ),
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
        """후처리 job 큐 사용 가능 여부를 반환한다."""

        return self._job_queue is not None

    def wait_for_dispatched_job(self, timeout_seconds: float) -> str | None:
        """큐에서 후처리 job 신호를 기다린다."""

        if self._job_queue is None:
            return None
        return self._job_queue.wait_for_job(timeout_seconds)

    def get_latest_job(self, session_id: str) -> SessionPostProcessingJob | None:
        """세션 기준 최신 후처리 job을 조회한다."""

        return self._repository.get_latest_by_session(session_id)

    def list_pending_jobs(self, limit: int = 10) -> list[SessionPostProcessingJob]:
        """처리 대기 중인 후처리 job 목록을 반환한다."""

        return self._repository.list_pending(limit=limit)

    def claim_available_jobs(
        self,
        *,
        worker_id: str,
        lease_duration_seconds: int,
        limit: int = 10,
    ) -> list[SessionPostProcessingJob]:
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
    ) -> list[SessionPostProcessingJob]:
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

    def process_latest_pending_for_session(
        self,
        session_id: str,
    ) -> SessionPostProcessingJob | None:
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
    ) -> SessionPostProcessingJob:
        """세션 후처리 job 하나를 처리한다."""

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

        self._ensure_processing_dependencies()

        started_session = self._session_repository.save(
            session.mark_post_processing_started(
                recording_artifact_id=processing_job.recording_artifact_id,
            )
        )

        try:
            recording_path = resolve_recording_reference(
                artifact_id=processing_job.recording_artifact_id,
                fallback_path=processing_job.recording_path,
                artifact_store=self._artifact_store,
            )
            if recording_path is None or not Path(recording_path).exists():
                raise ValueError("후처리할 원본 녹음 파일을 찾을 수 없습니다.")

            speaker_transcript = self._get_audio_postprocessing_service().build_speaker_transcript(
                recording_path
            )
            canonical_utterances = self._build_canonical_utterances(
                session_id=started_session.id,
                input_source=started_session.primary_input_source,
                processing_job_id=processing_job.id,
                speaker_transcript=speaker_transcript,
            )
            canonical_events = self._build_canonical_events(
                utterances=canonical_utterances,
                processing_job_id=processing_job.id,
            )

            self._utterance_repository.delete_by_session(started_session.id)
            for utterance in canonical_utterances:
                self._utterance_repository.save(utterance)

            self._event_repository.delete_by_session(started_session.id)
            for event in canonical_events:
                self._event_service.save_or_merge(event)

            completed_session = self._session_repository.save(
                started_session.mark_post_processing_completed(
                    recording_artifact_id=processing_job.recording_artifact_id,
                )
            )
            completed_job = self._repository.update(processing_job.mark_completed())

            report_generation_job_service = self._get_report_generation_job_service()
            if report_generation_job_service is not None:
                report_generation_job_service.enqueue_for_session(
                    session_id=completed_session.id,
                    requested_by_user_id=processing_job.requested_by_user_id,
                    dispatch=True,
                )

            return completed_job
        except Exception as error:
            logger.exception(
                "세션 후처리 job 처리 실패: session_id=%s job_id=%s worker_id=%s",
                processing_job.session_id,
                processing_job.id,
                expected_worker_id,
            )
            latest_session = self._session_repository.get_by_id(processing_job.session_id)
            if latest_session is not None:
                self._session_repository.save(
                    latest_session.mark_post_processing_failed(
                        str(error),
                        recording_artifact_id=processing_job.recording_artifact_id,
                    )
                )
            failed_job = processing_job.mark_failed(str(error))
            return self._repository.update(failed_job)

    def _resolve_processing_job(
        self,
        *,
        job_id: str,
        expected_worker_id: str | None,
    ) -> SessionPostProcessingJob:
        job = self._repository.get_by_id(job_id)
        if job is None:
            raise ValueError(f"세션 후처리 job을 찾을 수 없습니다: {job_id}")
        if job.status == "completed":
            return job

        if expected_worker_id is not None:
            if job.status != "processing":
                raise ValueError(f"claim되지 않은 세션 후처리 job입니다: {job_id}")
            if job.claimed_by_worker_id != expected_worker_id:
                raise ValueError(f"다른 worker가 claim한 세션 후처리 job입니다: {job_id}")
            return job

        if job.status == "processing":
            return job

        return self._repository.update(
            job.mark_processing(
                started_at=utc_now_iso(),
            )
        )

    def _resolve_recording_artifact(self, session_id: str):
        return find_session_recording_artifact(
            session_id,
            artifact_store=self._artifact_store,
        )

    def _build_canonical_utterances(
        self,
        *,
        session_id: str,
        input_source: str,
        processing_job_id: str,
        speaker_transcript,
    ) -> list[Utterance]:
        utterances: list[Utterance] = []
        for index, segment in enumerate(speaker_transcript, start=1):
            text = segment.text.strip()
            if not text:
                continue
            utterances.append(
                Utterance.create(
                    session_id=session_id,
                    seq_num=index,
                    start_ms=segment.start_ms,
                    end_ms=segment.end_ms,
                    text=text,
                    confidence=segment.confidence,
                    input_source=input_source,
                    stt_backend="post_processed",
                    latency_ms=None,
                    speaker_label=segment.speaker_label,
                    transcript_source="post_processed",
                    processing_job_id=processing_job_id,
                )
            )
        return utterances

    def _build_canonical_events(
        self,
        *,
        utterances: list[Utterance],
        processing_job_id: str,
    ) -> list[MeetingEvent]:
        analyzer = self._get_analyzer()
        if analyzer is None:
            return []

        finalized_at_ms = _now_ms()
        finalized_events: list[MeetingEvent] = []
        for utterance in utterances:
            for event in analyzer.analyze(utterance):
                finalized_events.append(
                    replace(
                        event,
                        source_utterance_id=utterance.id,
                        evidence_text=event.evidence_text or utterance.text,
                        speaker_label=utterance.speaker_label or event.speaker_label,
                        input_source=utterance.input_source or event.input_source,
                        insight_scope="finalized",
                        event_source="post_processed",
                        processing_job_id=processing_job_id,
                        finalized_at_ms=finalized_at_ms,
                    )
                )
        return finalized_events

    def _ensure_processing_dependencies(self) -> None:
        if self._utterance_repository is None:
            raise RuntimeError("후처리용 utterance repository가 필요합니다.")
        if self._event_repository is None or self._event_service is None:
            raise RuntimeError("후처리용 event repository가 필요합니다.")
        if self._audio_postprocessing_service is None and self._audio_postprocessing_service_factory is None:
            raise RuntimeError("후처리용 audio_postprocessing_service가 필요합니다.")

    def _get_audio_postprocessing_service(self) -> AudioPostprocessingService:
        if self._audio_postprocessing_service is None:
            if self._audio_postprocessing_service_factory is None:
                raise RuntimeError("후처리용 audio_postprocessing_service가 필요합니다.")
            self._audio_postprocessing_service = self._audio_postprocessing_service_factory()
        return self._audio_postprocessing_service

    def _get_analyzer(self) -> MeetingAnalyzer | None:
        if self._analyzer is None and self._analyzer_factory is not None:
            self._analyzer = self._analyzer_factory()
        return self._analyzer

    def _get_report_generation_job_service(self) -> ReportGenerationJobService | None:
        if (
            self._report_generation_job_service is None
            and self._report_generation_job_service_factory is not None
        ):
            self._report_generation_job_service = (
                self._report_generation_job_service_factory()
            )
        return self._report_generation_job_service
