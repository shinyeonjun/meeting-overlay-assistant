"""세션 후처리 파이프라인 stage helper를 제공한다."""
from __future__ import annotations

import logging
import time

from server.app.domain.models.session_post_processing_job import SessionPostProcessingJob
from server.app.services.post_meeting.canonical_builder import (
    build_canonical_events,
    build_canonical_utterances,
)
from server.app.services.post_meeting.provisional_transcript_writer import (
    ProvisionalTranscriptWriter,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    AudioPostprocessingService,
)


logger = logging.getLogger("server.app.services.post_meeting.session_post_processing_job_service")


def _now_ms() -> int:
    return int(time.time() * 1000)


class SessionPostProcessingPipelineStagesMixin:
    """후처리 job의 오디오/STT/canonical stage 세부 실행을 제공한다."""

    def _load_or_diarize_segments(
        self,
        *,
        session,
        job: SessionPostProcessingJob,
        recording_input,
        pipeline_signature: str,
        processed_audio,
        audio_postprocessing_service: AudioPostprocessingService,
    ):
        with self._stage_tracker.track(
            session=session,
            job=job,
            stage="diarize",
        ):
            cached_segments = self._stage_cache.load_diarized_segments(
                session_id=session.id,
                recording_artifact_id=job.recording_artifact_id,
                recording_sha256=recording_input.sha256,
                pipeline_signature=pipeline_signature,
                job_id=job.id,
            )
            if cached_segments is None:
                with self._hold_gpu_heavy_execution_slot(
                    owner=f"post_processing:{job.id}:diarize",
                ):
                    segments = audio_postprocessing_service.diarize_audio(
                        processed_audio,
                        audio_path=recording_input.path,
                    )
                self._stage_cache.save_diarized_segments(
                    session_id=session.id,
                    recording_artifact_id=job.recording_artifact_id,
                    recording_sha256=recording_input.sha256,
                    pipeline_signature=pipeline_signature,
                    segments=segments,
                    job_id=job.id,
                )
            else:
                segments = cached_segments
                logger.info(
                    "session post-processing diarize cache hit: session_id=%s job_id=%s segment_count=%s",
                    session.id,
                    job.id,
                    len(segments),
                )
            logger.info(
                "session post-processing diarize stage 산출: session_id=%s job_id=%s backend=%s segment_count=%s",
                session.id,
                job.id,
                type(audio_postprocessing_service).__name__,
                len(segments),
            )
            return segments

    def _load_or_transcribe_segments(
        self,
        *,
        session,
        job: SessionPostProcessingJob,
        recording_input,
        pipeline_signature: str,
        processed_audio,
        diarized_segments,
        audio_postprocessing_service: AudioPostprocessingService,
        provisional_writer: ProvisionalTranscriptWriter,
    ):
        with self._stage_tracker.track(
            session=session,
            job=job,
            stage="stt",
        ):
            cached_transcript = self._stage_cache.load_transcript_segments(
                session_id=session.id,
                recording_artifact_id=job.recording_artifact_id,
                recording_sha256=recording_input.sha256,
                pipeline_signature=pipeline_signature,
                job_id=job.id,
            )
            if cached_transcript is None:
                with self._hold_gpu_heavy_execution_slot(
                    owner=f"post_processing:{job.id}:stt",
                ):
                    speaker_transcript = (
                        audio_postprocessing_service.transcribe_segments(
                            processed_audio,
                            diarized_segments,
                            audio_path=recording_input.path,
                            on_segment=provisional_writer.persist,
                        )
                    )
                self._stage_cache.save_transcript_segments(
                    session_id=session.id,
                    recording_artifact_id=job.recording_artifact_id,
                    recording_sha256=recording_input.sha256,
                    pipeline_signature=pipeline_signature,
                    segments=speaker_transcript,
                    job_id=job.id,
                )
            else:
                speaker_transcript = cached_transcript
                for segment in speaker_transcript:
                    provisional_writer.persist(segment)
                logger.info(
                    "session post-processing stt cache hit: session_id=%s job_id=%s segment_count=%s",
                    session.id,
                    job.id,
                    len(speaker_transcript),
                )
            logger.info(
                "session post-processing stt stage 산출: session_id=%s job_id=%s backend=%s segment_count=%s provisional_segment_count=%s",
                session.id,
                job.id,
                type(audio_postprocessing_service).__name__,
                len(speaker_transcript),
                provisional_writer.sequence,
            )
            return speaker_transcript

    def _build_canonical_outputs(
        self,
        *,
        session,
        job: SessionPostProcessingJob,
        speaker_transcript,
    ):
        canonical_utterances = build_canonical_utterances(
            session_id=session.id,
            input_source=session.primary_input_source,
            processing_job_id=job.id,
            speaker_transcript=speaker_transcript,
        )
        canonical_events = build_canonical_events(
            utterances=canonical_utterances,
            processing_job_id=job.id,
            analyzer=self._get_analyzer(),
            finalized_at_ms=_now_ms(),
        )
        logger.info(
            "session post-processing canonical build 산출: session_id=%s job_id=%s utterance_count=%s event_count=%s",
            session.id,
            job.id,
            len(canonical_utterances),
            len(canonical_events),
        )
        return canonical_utterances, canonical_events

    def _enqueue_note_correction_followup(
        self,
        *,
        session,
        job: SessionPostProcessingJob,
    ) -> None:
        note_correction_job_service = self._get_note_correction_job_service()
        if note_correction_job_service is None:
            return

        followup_started_at = time.perf_counter()
        note_correction_job_service.enqueue_for_session(
            session_id=session.id,
            source_version=session.canonical_transcript_version,
            requested_by_user_id=job.requested_by_user_id,
            dispatch=True,
        )
        logger.info(
            "session post-processing followup enqueue 완료: session_id=%s job_id=%s source_version=%s elapsed_seconds=%.3f",
            session.id,
            job.id,
            session.canonical_transcript_version,
            time.perf_counter() - followup_started_at,
        )
