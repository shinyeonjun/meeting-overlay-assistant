"""후처리 heavy stage cache 접근을 안전하게 감싼다."""

from __future__ import annotations

import logging

from server.app.services.diarization.speaker_diarizer import SpeakerSegment
from server.app.services.post_meeting.post_processing_stage_cache import (
    PostProcessingStageCacheStore,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)


logger = logging.getLogger(__name__)


class PostProcessingStageCache:
    """stage cache signature 계산과 load/save 실패 격리를 담당한다."""

    def __init__(self, store: PostProcessingStageCacheStore) -> None:
        self._store = store

    def build_pipeline_signature(self, audio_postprocessing_service) -> str:
        signature_builder = getattr(
            audio_postprocessing_service,
            "build_stage_cache_signature",
            None,
        )
        if callable(signature_builder):
            return str(signature_builder())
        service_type = type(audio_postprocessing_service)
        return f"{service_type.__module__}.{service_type.__qualname__}"

    def load_diarized_segments(
        self,
        *,
        session_id: str,
        recording_artifact_id: str | None,
        recording_sha256: str,
        pipeline_signature: str,
        job_id: str,
    ) -> list[SpeakerSegment] | None:
        try:
            return self._store.load_diarized_segments(
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

    def save_diarized_segments(
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
            self._store.save_diarized_segments(
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

    def load_transcript_segments(
        self,
        *,
        session_id: str,
        recording_artifact_id: str | None,
        recording_sha256: str,
        pipeline_signature: str,
        job_id: str,
    ) -> list[SpeakerTranscriptSegment] | None:
        try:
            return self._store.load_transcript_segments(
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

    def save_transcript_segments(
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
            self._store.save_transcript_segments(
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
