"""session post-processing 중간 산출물 cache 저장소."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict
from pathlib import Path

from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.services.diarization.speaker_diarizer import SpeakerSegment
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)


_CACHE_SCHEMA_VERSION = 1


def compute_file_sha256(path: str | Path) -> str:
    """녹음 파일 동일성 검사용 SHA-256을 계산한다."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class PostProcessingStageCacheStore:
    """후처리 heavy stage 결과를 session artifact로 저장하고 재사용한다."""

    def __init__(self, artifact_store: LocalArtifactStore) -> None:
        self._artifact_store = artifact_store

    def load_diarized_segments(
        self,
        *,
        session_id: str,
        recording_artifact_id: str | None,
        recording_sha256: str,
        pipeline_signature: str,
    ) -> list[SpeakerSegment] | None:
        payload = self._load_payload(
            session_id=session_id,
            stage="diarize",
            recording_artifact_id=recording_artifact_id,
            recording_sha256=recording_sha256,
            pipeline_signature=pipeline_signature,
        )
        if payload is None:
            return None
        return [
            SpeakerSegment(
                speaker_label=str(item.get("speaker_label") or "UNKNOWN"),
                start_ms=int(item.get("start_ms") or 0),
                end_ms=int(item.get("end_ms") or 0),
            )
            for item in (payload.get("segments") or [])
        ]

    def save_diarized_segments(
        self,
        *,
        session_id: str,
        recording_artifact_id: str | None,
        recording_sha256: str,
        pipeline_signature: str,
        segments: list[SpeakerSegment],
    ) -> None:
        self._save_payload(
            session_id=session_id,
            stage="diarize",
            recording_artifact_id=recording_artifact_id,
            recording_sha256=recording_sha256,
            pipeline_signature=pipeline_signature,
            segments=[asdict(segment) for segment in segments],
        )

    def load_transcript_segments(
        self,
        *,
        session_id: str,
        recording_artifact_id: str | None,
        recording_sha256: str,
        pipeline_signature: str,
    ) -> list[SpeakerTranscriptSegment] | None:
        payload = self._load_payload(
            session_id=session_id,
            stage="stt",
            recording_artifact_id=recording_artifact_id,
            recording_sha256=recording_sha256,
            pipeline_signature=pipeline_signature,
        )
        if payload is None:
            return None
        return [
            SpeakerTranscriptSegment(
                speaker_label=str(item.get("speaker_label") or "UNKNOWN"),
                start_ms=int(item.get("start_ms") or 0),
                end_ms=int(item.get("end_ms") or 0),
                text=str(item.get("text") or ""),
                confidence=float(item.get("confidence") or 0.0),
            )
            for item in (payload.get("segments") or [])
        ]

    def save_transcript_segments(
        self,
        *,
        session_id: str,
        recording_artifact_id: str | None,
        recording_sha256: str,
        pipeline_signature: str,
        segments: list[SpeakerTranscriptSegment],
    ) -> None:
        self._save_payload(
            session_id=session_id,
            stage="stt",
            recording_artifact_id=recording_artifact_id,
            recording_sha256=recording_sha256,
            pipeline_signature=pipeline_signature,
            segments=[asdict(segment) for segment in segments],
        )

    def delete(self, session_id: str) -> None:
        target_dir = self._artifact_store.resolve_path(
            f"post_processing_stage_cache/{session_id}"
        )
        shutil.rmtree(target_dir, ignore_errors=True)

    def _load_payload(
        self,
        *,
        session_id: str,
        stage: str,
        recording_artifact_id: str | None,
        recording_sha256: str,
        pipeline_signature: str,
    ) -> dict | None:
        target_path = self._resolve_path(session_id=session_id, stage=stage)
        if not target_path.exists():
            return None
        try:
            payload = json.loads(target_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None
        if payload.get("schema_version") != _CACHE_SCHEMA_VERSION:
            return None
        if str(payload.get("session_id") or "") != session_id:
            return None
        if (payload.get("recording_artifact_id") or None) != recording_artifact_id:
            return None
        if str(payload.get("recording_sha256") or "") != recording_sha256:
            return None
        if str(payload.get("pipeline_signature") or "") != pipeline_signature:
            return None
        return payload

    def _save_payload(
        self,
        *,
        session_id: str,
        stage: str,
        recording_artifact_id: str | None,
        recording_sha256: str,
        pipeline_signature: str,
        segments: list[dict],
    ) -> None:
        target_path = self._resolve_path(session_id=session_id, stage=stage)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": _CACHE_SCHEMA_VERSION,
            "session_id": session_id,
            "stage": stage,
            "recording_artifact_id": recording_artifact_id,
            "recording_sha256": recording_sha256,
            "pipeline_signature": pipeline_signature,
            "segments": segments,
        }
        target_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _resolve_path(self, *, session_id: str, stage: str) -> Path:
        artifact_id = f"post_processing_stage_cache/{session_id}/{stage}.json"
        return self._artifact_store.resolve_path(artifact_id)
