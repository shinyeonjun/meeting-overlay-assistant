"""공통 영역의 session post processing job service 서비스를 제공한다."""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, replace
from pathlib import Path

from server.app.core.config import settings
from server.app.domain.events import MeetingEvent
from server.app.domain.models.session_post_processing_job import SessionPostProcessingJob
from server.app.domain.models.utterance import Utterance
from server.app.domain.session import MeetingSession
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
from server.app.services.post_meeting.post_processing_stage_cache import (
    PostProcessingStageCacheStore,
    compute_file_sha256,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    AudioPostprocessingService,
    SpeakerTranscriptSegment,
)
from server.app.services.diarization.speaker_diarizer import SpeakerSegment
from server.app.services.reports.jobs.helpers.time_utils import (
    utc_after_seconds_iso,
    utc_now_iso,
)
from server.app.services.reports.jobs.note_correction_job_service import (
    NoteCorrectionJobService,
)
from server.app.services.reports.refinement import (
    TranscriptCorrectionDocument,
    TranscriptCorrectionStore,
)
from server.app.services.sessions.workspace_summary_models import (
    WorkspaceSummaryDocument,
)
from server.app.services.sessions.workspace_summary_store import WorkspaceSummaryStore


logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True)
class _CanonicalStateSnapshot:
    utterances: tuple[Utterance, ...]
    events: tuple[MeetingEvent, ...]
    correction_document: TranscriptCorrectionDocument | None
    workspace_summary_document: WorkspaceSummaryDocument | None


class SessionPostProcessingJobService:
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
        self._live_session_wait_timeout_seconds = max(
            live_session_wait_timeout_seconds,
            0.0,
        )
        self._live_session_poll_interval_seconds = max(
            live_session_poll_interval_seconds,
            0.1,
        )
        self._job_queue = job_queue
        self._artifact_store = artifact_store or LocalArtifactStore(settings.artifacts_root_path)
        self._transcript_correction_store = transcript_correction_store
        self._workspace_summary_store = workspace_summary_store
        self._post_processing_stage_cache_store = (
            post_processing_stage_cache_store
            or PostProcessingStageCacheStore(self._artifact_store)
        )
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

        self._wait_for_live_sessions_quiet_period(
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
        previous_canonical_state = self._snapshot_canonical_state(started_session.id)

        try:
            provisional_sequence = 0
            with self._track_post_processing_stage(
                session=started_session,
                job=processing_job,
                stage="prepare",
            ):
                recording_path = resolve_recording_reference(
                    artifact_id=processing_job.recording_artifact_id,
                    fallback_path=processing_job.recording_path,
                    artifact_store=self._artifact_store,
                )
                if recording_path is None or not Path(recording_path).exists():
                    raise ValueError("후처리할 원본 녹음 파일을 찾을 수 없습니다.")

                recording_size_bytes = Path(recording_path).stat().st_size
                recording_sha256 = compute_file_sha256(recording_path)
                logger.info(
                    "session post-processing 입력 녹음 확인: session_id=%s job_id=%s path=%s size_bytes=%s sha256=%s",
                    started_session.id,
                    processing_job.id,
                    recording_path,
                    recording_size_bytes,
                    recording_sha256,
                )

                # 진행 중 초안은 최종 canonical transcript와 충돌하지 않도록
                # 별도 source로 먼저 저장하고, 완료 시점에 한 번에 승격한다.
                self._prepare_provisional_transcript(session_id=started_session.id)

            def persist_provisional_segment(segment) -> None:
                nonlocal provisional_sequence
                text = segment.text.strip()
                if not text:
                    return
                provisional_sequence += 1
                self._utterance_repository.save(
                    Utterance.create(
                        session_id=started_session.id,
                        seq_num=provisional_sequence,
                        start_ms=segment.start_ms,
                        end_ms=segment.end_ms,
                        text=text,
                        confidence=segment.confidence,
                        input_source=started_session.primary_input_source,
                        stt_backend="post_processed",
                        latency_ms=None,
                        speaker_label=segment.speaker_label,
                        transcript_source="post_processing_draft",
                        processing_job_id=processing_job.id,
                    )
                )

            audio_postprocessing_service = self._get_audio_postprocessing_service()
            pipeline_signature = self._build_stage_cache_signature(
                audio_postprocessing_service
            )
            with self._track_post_processing_stage(
                session=started_session,
                job=processing_job,
                stage="load_audio",
            ):
                processed_audio = audio_postprocessing_service.load_audio(recording_path)
            with self._track_post_processing_stage(
                session=started_session,
                job=processing_job,
                stage="diarize",
            ):
                cached_diarized_segments = self._load_cached_diarized_segments(
                    session_id=started_session.id,
                    recording_artifact_id=processing_job.recording_artifact_id,
                    recording_sha256=recording_sha256,
                    pipeline_signature=pipeline_signature,
                    job_id=processing_job.id,
                )
                if cached_diarized_segments is None:
                    with self._hold_gpu_heavy_execution_slot(
                        owner=f"post_processing:{processing_job.id}:diarize",
                    ):
                        diarized_segments = audio_postprocessing_service.diarize_audio(
                            processed_audio,
                            audio_path=recording_path,
                        )
                    self._save_cached_diarized_segments(
                        session_id=started_session.id,
                        recording_artifact_id=processing_job.recording_artifact_id,
                        recording_sha256=recording_sha256,
                        pipeline_signature=pipeline_signature,
                        segments=diarized_segments,
                        job_id=processing_job.id,
                    )
                else:
                    diarized_segments = cached_diarized_segments
                    logger.info(
                        "session post-processing diarize cache hit: session_id=%s job_id=%s segment_count=%s",
                        started_session.id,
                        processing_job.id,
                        len(diarized_segments),
                    )
                logger.info(
                    "session post-processing diarize stage 산출: session_id=%s job_id=%s backend=%s segment_count=%s",
                    started_session.id,
                    processing_job.id,
                    type(audio_postprocessing_service).__name__,
                    len(diarized_segments),
                )
            with self._track_post_processing_stage(
                session=started_session,
                job=processing_job,
                stage="stt",
            ):
                cached_speaker_transcript = self._load_cached_transcript_segments(
                    session_id=started_session.id,
                    recording_artifact_id=processing_job.recording_artifact_id,
                    recording_sha256=recording_sha256,
                    pipeline_signature=pipeline_signature,
                    job_id=processing_job.id,
                )
                if cached_speaker_transcript is None:
                    with self._hold_gpu_heavy_execution_slot(
                        owner=f"post_processing:{processing_job.id}:stt",
                    ):
                        speaker_transcript = audio_postprocessing_service.transcribe_segments(
                            processed_audio,
                            diarized_segments,
                            audio_path=recording_path,
                            on_segment=persist_provisional_segment,
                        )
                    self._save_cached_transcript_segments(
                        session_id=started_session.id,
                        recording_artifact_id=processing_job.recording_artifact_id,
                        recording_sha256=recording_sha256,
                        pipeline_signature=pipeline_signature,
                        segments=speaker_transcript,
                        job_id=processing_job.id,
                    )
                else:
                    speaker_transcript = cached_speaker_transcript
                    for segment in speaker_transcript:
                        persist_provisional_segment(segment)
                    logger.info(
                        "session post-processing stt cache hit: session_id=%s job_id=%s segment_count=%s",
                        started_session.id,
                        processing_job.id,
                        len(speaker_transcript),
                    )
                logger.info(
                    "session post-processing stt stage 산출: session_id=%s job_id=%s backend=%s segment_count=%s provisional_segment_count=%s",
                    started_session.id,
                    processing_job.id,
                    type(audio_postprocessing_service).__name__,
                    len(speaker_transcript),
                    provisional_sequence,
                )
            with self._track_post_processing_stage(
                session=started_session,
                job=processing_job,
                stage="build",
            ):
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
                logger.info(
                    "session post-processing canonical build 산출: session_id=%s job_id=%s utterance_count=%s event_count=%s",
                    started_session.id,
                    processing_job.id,
                    len(canonical_utterances),
                    len(canonical_events),
                )

            with self._track_post_processing_stage(
                session=started_session,
                job=processing_job,
                stage="persist",
            ):
                # 전체 전사가 끝나면 provisional rows를 final canonical rows로 교체한다.
                self._replace_canonical_state(
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

            note_correction_job_service = self._get_note_correction_job_service()
            if note_correction_job_service is not None:
                followup_started_at = time.perf_counter()
                note_correction_job_service.enqueue_for_session(
                    session_id=completed_session.id,
                    source_version=completed_session.canonical_transcript_version,
                    requested_by_user_id=processing_job.requested_by_user_id,
                    dispatch=True,
                )
                logger.info(
                    "session post-processing followup enqueue 완료: session_id=%s job_id=%s source_version=%s elapsed_seconds=%.3f",
                    completed_session.id,
                    processing_job.id,
                    completed_session.canonical_transcript_version,
                    time.perf_counter() - followup_started_at,
                )

            logger.info(
                "session post-processing 전체 완료: session_id=%s job_id=%s elapsed_seconds=%.3f",
                completed_session.id,
                processing_job.id,
                time.perf_counter() - total_started_at,
            )

            return completed_job
        except Exception as error:
            logger.exception(
                "세션 후처리 job 처리 실패: session_id=%s job_id=%s worker_id=%s",
                processing_job.session_id,
                processing_job.id,
                expected_worker_id,
            )
            self._restore_canonical_state(
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

    def _build_stage_cache_signature(
        self,
        audio_postprocessing_service,
    ) -> str:
        signature_builder = getattr(
            audio_postprocessing_service,
            "build_stage_cache_signature",
            None,
        )
        if callable(signature_builder):
            return str(signature_builder())
        service_type = type(audio_postprocessing_service)
        return f"{service_type.__module__}.{service_type.__qualname__}"

    def _load_cached_diarized_segments(
        self,
        *,
        session_id: str,
        recording_artifact_id: str | None,
        recording_sha256: str,
        pipeline_signature: str,
        job_id: str,
    ) -> list[SpeakerSegment] | None:
        try:
            return self._post_processing_stage_cache_store.load_diarized_segments(
                session_id=session_id,
                recording_artifact_id=recording_artifact_id,
                recording_sha256=recording_sha256,
                pipeline_signature=pipeline_signature,
            )
        except Exception:
            logger.warning(
                "session post-processing diarize cache load 실패: session_id=%s job_id=%s",
                session_id,
                job_id,
                exc_info=True,
            )
            return None

    def _save_cached_diarized_segments(
        self,
        *,
        session_id: str,
        recording_artifact_id: str | None,
        recording_sha256: str,
        pipeline_signature: str,
        segments: list[SpeakerSegment],
        job_id: str,
    ) -> None:
        try:
            self._post_processing_stage_cache_store.save_diarized_segments(
                session_id=session_id,
                recording_artifact_id=recording_artifact_id,
                recording_sha256=recording_sha256,
                pipeline_signature=pipeline_signature,
                segments=segments,
            )
        except Exception:
            logger.warning(
                "session post-processing diarize cache save 실패: session_id=%s job_id=%s",
                session_id,
                job_id,
                exc_info=True,
            )

    def _load_cached_transcript_segments(
        self,
        *,
        session_id: str,
        recording_artifact_id: str | None,
        recording_sha256: str,
        pipeline_signature: str,
        job_id: str,
    ) -> list[SpeakerTranscriptSegment] | None:
        try:
            return self._post_processing_stage_cache_store.load_transcript_segments(
                session_id=session_id,
                recording_artifact_id=recording_artifact_id,
                recording_sha256=recording_sha256,
                pipeline_signature=pipeline_signature,
            )
        except Exception:
            logger.warning(
                "session post-processing stt cache load 실패: session_id=%s job_id=%s",
                session_id,
                job_id,
                exc_info=True,
            )
            return None

    def _save_cached_transcript_segments(
        self,
        *,
        session_id: str,
        recording_artifact_id: str | None,
        recording_sha256: str,
        pipeline_signature: str,
        segments: list[SpeakerTranscriptSegment],
        job_id: str,
    ) -> None:
        try:
            self._post_processing_stage_cache_store.save_transcript_segments(
                session_id=session_id,
                recording_artifact_id=recording_artifact_id,
                recording_sha256=recording_sha256,
                pipeline_signature=pipeline_signature,
                segments=segments,
            )
        except Exception:
            logger.warning(
                "session post-processing stt cache save 실패: session_id=%s job_id=%s",
                session_id,
                job_id,
                exc_info=True,
            )

    @contextmanager
    def _track_post_processing_stage(
        self,
        *,
        session: MeetingSession,
        job: SessionPostProcessingJob,
        stage: str,
    ):
        staged_session = self._session_repository.save(
            session.mark_post_processing_stage(stage)
        )
        started_at = time.perf_counter()
        logger.info(
            "session post-processing stage 시작: session_id=%s job_id=%s stage=%s status=%s",
            session.id,
            job.id,
            stage,
            staged_session.post_processing_status,
        )
        try:
            yield staged_session
        except Exception as error:
            logger.warning(
                "session post-processing stage 실패: session_id=%s job_id=%s stage=%s elapsed_seconds=%.3f error=%s",
                session.id,
                job.id,
                stage,
                time.perf_counter() - started_at,
                error,
            )
            raise
        else:
            logger.info(
                "session post-processing stage 완료: session_id=%s job_id=%s stage=%s elapsed_seconds=%.3f",
                session.id,
                job.id,
                stage,
                time.perf_counter() - started_at,
            )

    def _should_defer_claim_for_live_sessions(self, *, worker_id: str) -> bool:
        running_session_count = self._session_repository.count_running()
        if running_session_count <= 0:
            return False

        logger.info(
            "session post-processing job claim 보류: worker_id=%s running_session_count=%s",
            worker_id,
            running_session_count,
        )
        return True

    def _wait_for_live_sessions_quiet_period(
        self,
        *,
        job_id: str,
        session_id: str,
    ) -> None:
        running_session_count = self._session_repository.count_running()
        if running_session_count <= 0:
            return

        deadline = time.monotonic() + self._live_session_wait_timeout_seconds
        logger.info(
            "session post-processing live 대기 시작: job_id=%s session_id=%s timeout_seconds=%.1f poll_seconds=%.1f running_session_count=%s",
            job_id,
            session_id,
            self._live_session_wait_timeout_seconds,
            self._live_session_poll_interval_seconds,
            running_session_count,
        )

        while running_session_count > 0:
            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0:
                logger.warning(
                    "session post-processing live 대기시간 초과, 기존 흐름으로 진행: job_id=%s session_id=%s timeout_seconds=%.1f running_session_count=%s",
                    job_id,
                    session_id,
                    self._live_session_wait_timeout_seconds,
                    running_session_count,
                )
                return
            time.sleep(min(self._live_session_poll_interval_seconds, remaining_seconds))
            running_session_count = self._session_repository.count_running()

        waited_seconds = max(
            self._live_session_wait_timeout_seconds
            - max(deadline - time.monotonic(), 0.0),
            0.0,
        )
        logger.info(
            "session post-processing live 대기 종료: job_id=%s session_id=%s waited_seconds=%.3f",
            job_id,
            session_id,
            waited_seconds,
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

    def _clear_transcript_corrections(self, session_id: str) -> None:
        if self._transcript_correction_store is None:
            return
        self._transcript_correction_store.delete(session_id)

    def _clear_workspace_summary(self, session_id: str) -> None:
        if self._workspace_summary_store is None:
            return
        self._workspace_summary_store.delete(session_id)

    def _snapshot_canonical_state(self, session_id: str) -> _CanonicalStateSnapshot:
        return _CanonicalStateSnapshot(
            utterances=tuple(self._utterance_repository.list_by_session(session_id)),
            events=tuple(self._event_repository.list_by_session(session_id)),
            correction_document=(
                self._transcript_correction_store.load(session_id=session_id)
                if self._transcript_correction_store is not None
                else None
            ),
            workspace_summary_document=(
                self._workspace_summary_store.load(session_id=session_id)
                if self._workspace_summary_store is not None
                else None
            ),
        )

    def _replace_canonical_state(
        self,
        *,
        session_id: str,
        utterances: list[Utterance],
        events: list[MeetingEvent],
    ) -> None:
        self._clear_transcript_corrections(session_id)
        self._clear_workspace_summary(session_id)
        self._utterance_repository.delete_by_session(session_id)
        for utterance in utterances:
            self._utterance_repository.save(utterance)

        self._event_repository.delete_by_session(session_id)
        for event in events:
            self._event_service.save_or_merge(event)

    def _prepare_provisional_transcript(self, *, session_id: str) -> None:
        self._clear_transcript_corrections(session_id)
        self._clear_workspace_summary(session_id)
        self._utterance_repository.delete_by_session(session_id)
        self._event_repository.delete_by_session(session_id)

    def _restore_canonical_state(
        self,
        *,
        session_id: str,
        snapshot: _CanonicalStateSnapshot,
    ) -> None:
        try:
            self._clear_transcript_corrections(session_id)
            self._utterance_repository.delete_by_session(session_id)
            for utterance in snapshot.utterances:
                self._utterance_repository.save(utterance)

            self._event_repository.delete_by_session(session_id)
            for event in snapshot.events:
                self._event_repository.save(event)

            if self._transcript_correction_store is not None:
                if snapshot.correction_document is None:
                    self._transcript_correction_store.delete(session_id)
                else:
                    self._transcript_correction_store.save(snapshot.correction_document)
            if self._workspace_summary_store is not None:
                if snapshot.workspace_summary_document is None:
                    self._workspace_summary_store.delete(session_id)
                else:
                    self._workspace_summary_store.save(snapshot.workspace_summary_document)
        except Exception:
            logger.exception(
                "canonical transcript/event 복구 실패: session_id=%s",
                session_id,
            )

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
