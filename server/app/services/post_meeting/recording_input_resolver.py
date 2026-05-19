"""세션 후처리 입력 녹음 파일을 해석한다."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from server.app.domain.models.session_post_processing_job import (
    SessionPostProcessingJob,
)
from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.services.audio.io.session_recording import resolve_recording_reference
from server.app.services.post_meeting.post_processing_stage_cache import (
    compute_file_sha256,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PostProcessingRecordingInput:
    """후처리 stage에서 재사용하는 입력 녹음 메타데이터."""

    path: Path
    size_bytes: int
    sha256: str


class PostProcessingRecordingInputResolver:
    """job에 기록된 artifact id 또는 fallback path로 입력 녹음을 찾는다."""

    def __init__(self, artifact_store: LocalArtifactStore) -> None:
        self._artifact_store = artifact_store

    def resolve(
        self,
        *,
        session_id: str,
        job: SessionPostProcessingJob,
    ) -> PostProcessingRecordingInput:
        recording_path = resolve_recording_reference(
            artifact_id=job.recording_artifact_id,
            fallback_path=job.recording_path,
            artifact_store=self._artifact_store,
        )
        if recording_path is None or not Path(recording_path).exists():
            raise ValueError("후처리할 원본 녹음 파일을 찾을 수 없습니다.")

        resolved_path = Path(recording_path)
        recording_input = PostProcessingRecordingInput(
            path=resolved_path,
            size_bytes=resolved_path.stat().st_size,
            sha256=compute_file_sha256(resolved_path),
        )
        logger.info(
            "session post-processing 입력 녹음 확인: session_id=%s job_id=%s path=%s size_bytes=%s sha256=%s",
            session_id,
            job.id,
            recording_input.path,
            recording_input.size_bytes,
            recording_input.sha256,
        )
        return recording_input
