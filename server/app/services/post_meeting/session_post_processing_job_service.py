"""공통 영역의 session post processing job service 서비스를 제공한다."""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from contextlib import nullcontext

from server.app.core.config import settings
from server.app.domain.models.session_post_processing_job import SessionPostProcessingJob
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
)
from server.app.services.events.meeting_event_service import MeetingEventService
from server.app.services.post_meeting.canonical_state_store import CanonicalStateStore
from server.app.services.post_meeting.live_session_quiet_period import (
    LiveSessionQuietPeriod,
)
from server.app.services.post_meeting.post_processing_stage_tracker import (
    PostProcessingStageTracker,
)
from server.app.services.post_meeting.provisional_transcript_writer import (
    ProvisionalTranscriptWriter,
)
from server.app.services.post_meeting.session_post_processing_pipeline_stages import (
    SessionPostProcessingPipelineStagesMixin,
)
from server.app.services.post_meeting.session_post_processing_job_queue import (
    SessionPostProcessingJobQueue,
)
from server.app.services.post_meeting.post_processing_stage_cache import (
    PostProcessingStageCacheStore,
)
from server.app.services.post_meeting.recording_input_resolver import (
    PostProcessingRecordingInputResolver,
)
from server.app.services.post_meeting.stage_cache_access import (
    PostProcessingStageCache,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    AudioPostprocessingService,
)
from server.app.services.reports.jobs.helpers.time_utils import (
    utc_after_seconds_iso,
    utc_now_iso,
)
from server.app.services.reports.jobs.note_correction_job_service import (
    NoteCorrectionJobService,
)
from server.app.services.reports.refinement import (
    TranscriptCorrectionStore,
)
from server.app.services.sessions.workspace_summary_store import WorkspaceSummaryStore


logger = logging.getLogger(__name__)

class SessionPostProcessingJobService(SessionPostProcessingPipelineStagesMixin):
    """녹음 아티팩트 기준으로 세션 후처리 파이프라인을 실행한다.

    이 서비스는 raw 오디오를 다시 읽어 transcript/event를 재생성하고,
    이후 단계인 note correction과 report generation으로 흐름을 넘긴다.
    """

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
        note_correction_job_service: (
            NoteCorrectionJobService | Callable[[], NoteCorrectionJobService | None] | None
        ) = None,
        gpu_heavy_execution_gate=None,
        gpu_heavy_poll_interval_seconds: float = 1.0,
        live_session_wait_timeout_seconds: float = 300.0,
        live_session_poll_interval_seconds: float = 5.0,
        job_queue: SessionPostProcessingJobQueue | None = None,
        artifact_store: LocalArtifactStore | None = None,
        transcript_correction_store: TranscriptCorrectionStore | None = None,
        workspace_summary_store: WorkspaceSummaryStore | None = None,
        post_processing_stage_cache_store: PostProcessingStageCacheStore | None = None,
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
        self._note_correction_job_service = (
            None if callable(note_correction_job_service) else note_correction_job_service
        )
        self._note_correction_job_service_factory = (
            note_correction_job_service if callable(note_correction_job_service) else None
        )
        self._gpu_heavy_execution_gate = gpu_heavy_execution_gate
        self._gpu_heavy_poll_interval_seconds = max(
            gpu_heavy_poll_interval_seconds,
            0.1,
        )
        self._live_session_quiet_period = LiveSessionQuietPeriod(
            session_repository=session_repository,
            wait_timeout_seconds=live_session_wait_timeout_seconds,
            poll_interval_seconds=live_session_poll_interval_seconds,
        )
        self._stage_tracker = PostProcessingStageTracker(session_repository)
        self._job_queue = job_queue
        self._artifact_store = artifact_store or LocalArtifactStore(
            settings.artifacts_root_path
        )
        self._recording_input_resolver = PostProcessingRecordingInputResolver(
            self._artifact_store
        )
        stage_cache_store = (
            post_processing_stage_cache_store
            or PostProcessingStageCacheStore(self._artifact_store)
        )
        self._stage_cache = PostProcessingStageCache(stage_cache_store)
        self._event_service = (
            MeetingEventService(event_repository)
            if event_repository is not None
            else None
        )
        self._canonical_state_store = CanonicalStateStore(
            utterance_repository=utterance_repository,
            event_repository=event_repository,
            event_service=self._event_service,
            transcript_correction_store=transcript_correction_store,
            workspace_summary_store=workspace_summary_store,
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
        if latest_job is not None and latest_job.status == "processing":
            return latest_job
        if latest_job is not None and latest_job.status == "pending":
            self._session_repository.save(
                session.queue_post_processing(
                    recording_artifact_id=latest_job.recording_artifact_id,
                )
            )
            if dispatch:
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
        """후처리 job 큐 사용 여부를 반환한다."""

        return self._job_queue is not None

    def wait_for_dispatched_job(self, timeout_seconds: float) -> str | None:
        """큐에서 후처리 job 신호를 기다린다."""

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
        """처리 중인 job lease를 연장한다."""

        return self._repository.renew_lease(
            job_id=job_id,
            worker_id=worker_id,
            lease_expires_at=utc_after_seconds_iso(lease_duration_seconds),
        )

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

        if self._live_session_quiet_period.should_defer_claim(worker_id=worker_id):
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

        self._live_session_quiet_period.wait(
            job_id=processing_job.id,
            session_id=processing_job.session_id,
        )
        self._ensure_processing_dependencies()

        total_started_at = time.perf_counter()
        started_session = self._session_repository.save(
            session.mark_post_processing_started(
                recording_artifact_id=processing_job.recording_artifact_id,
            )
        )
        previous_canonical_state = self._canonical_state_store.snapshot(
            started_session.id
        )

        try:
            with self._stage_tracker.track(
                session=started_session,
                job=processing_job,
                stage="prepare",
            ):
                recording_input = self._recording_input_resolver.resolve(
                    session_id=started_session.id,
                    job=processing_job,
                )

                # 진행 중 초안은 최종 canonical transcript와 충돌하지 않도록
                # 별도 source로 먼저 저장하고, 완료 시점에 한 번에 승격한다.
                self._canonical_state_store.prepare_provisional_transcript(
                    session_id=started_session.id
                )

            provisional_writer = self._build_provisional_transcript_writer(
                session_id=started_session.id,
                input_source=started_session.primary_input_source,
                processing_job_id=processing_job.id,
            )

            audio_postprocessing_service = self._get_audio_postprocessing_service()
            pipeline_signature = self._stage_cache.build_pipeline_signature(
                audio_postprocessing_service
            )
            with self._stage_tracker.track(
                session=started_session,
                job=processing_job,
                stage="load_audio",
            ):
                processed_audio = audio_postprocessing_service.load_audio(
                    recording_input.path
                )
            diarized_segments = self._load_or_diarize_segments(
                session=started_session,
                job=processing_job,
                recording_input=recording_input,
                pipeline_signature=pipeline_signature,
                processed_audio=processed_audio,
                audio_postprocessing_service=audio_postprocessing_service,
            )
            speaker_transcript = self._load_or_transcribe_segments(
                session=started_session,
                job=processing_job,
                recording_input=recording_input,
                pipeline_signature=pipeline_signature,
                processed_audio=processed_audio,
                diarized_segments=diarized_segments,
                audio_postprocessing_service=audio_postprocessing_service,
                provisional_writer=provisional_writer,
            )
            with self._stage_tracker.track(
                session=started_session,
                job=processing_job,
                stage="build",
            ):
                canonical_utterances, canonical_events = (
                    self._build_canonical_outputs(
                        session=started_session,
                        job=processing_job,
                        speaker_transcript=speaker_transcript,
                    )
                )

            with self._stage_tracker.track(
                session=started_session,
                job=processing_job,
                stage="persist",
            ):
                # 전체 전사가 끝나면 provisional rows를 final canonical rows로 교체한다.
                self._canonical_state_store.replace(
                    session_id=started_session.id,
                    utterances=canonical_utterances,
                    events=canonical_events,
                )

            completed_session = self._session_repository.save(
                started_session.mark_post_processing_completed(
                    recording_artifact_id=processing_job.recording_artifact_id,
                )
            )
            completed_job = self._repository.update(processing_job.mark_completed())

            self._enqueue_note_correction_followup(
                session=completed_session,
                job=processing_job,
            )

            logger.info(
                "session post-processing 전체 완료: session_id=%s job_id=%s elapsed_seconds=%.3f",
                completed_session.id,
                processing_job.id,
                time.perf_counter() - total_started_at,
            )

            return completed_job
        except Exception as error:
            return self._mark_failed_after_processing_error(
                processing_job=processing_job,
                previous_canonical_state=previous_canonical_state,
                error=error,
                expected_worker_id=expected_worker_id,
            )

    def _mark_failed_after_processing_error(
        self,
        *,
        processing_job: SessionPostProcessingJob,
        previous_canonical_state,
        error: Exception,
        expected_worker_id: str | None,
    ) -> SessionPostProcessingJob:
        logger.exception(
            "세션 후처리 job 처리 실패: session_id=%s job_id=%s worker_id=%s",
            processing_job.session_id,
            processing_job.id,
            expected_worker_id,
        )
        self._canonical_state_store.restore(
            session_id=processing_job.session_id,
            snapshot=previous_canonical_state,
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

    def _hold_gpu_heavy_execution_slot(self, *, owner: str):
        gate = self._gpu_heavy_execution_gate
        if gate is None:
            return nullcontext()
        return gate.hold(
            owner=owner,
            poll_interval_seconds=self._gpu_heavy_poll_interval_seconds,
        )

    def _ensure_processing_dependencies(self) -> None:
        if self._utterance_repository is None:
            raise RuntimeError("후처리용 utterance repository가 필요합니다.")
        if self._event_repository is None or self._event_service is None:
            raise RuntimeError("후처리용 event repository가 필요합니다.")
        if self._audio_postprocessing_service is None and self._audio_postprocessing_service_factory is None:
            raise RuntimeError("후처리용 audio_postprocessing_service가 필요합니다.")

    def _build_provisional_transcript_writer(
        self,
        *,
        session_id: str,
        input_source: str,
        processing_job_id: str,
    ) -> ProvisionalTranscriptWriter:
        if self._utterance_repository is None:
            raise RuntimeError("후처리용 utterance repository가 필요합니다.")
        return ProvisionalTranscriptWriter(
            utterance_repository=self._utterance_repository,
            session_id=session_id,
            input_source=input_source,
            processing_job_id=processing_job_id,
        )

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

    def _get_note_correction_job_service(self) -> NoteCorrectionJobService | None:
        if (
            self._note_correction_job_service is None
            and self._note_correction_job_service_factory is not None
        ):
            self._note_correction_job_service = (
                self._note_correction_job_service_factory()
            )
        return self._note_correction_job_service
