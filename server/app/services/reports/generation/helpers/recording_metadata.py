"""회의록 생성에 필요한 녹음 파일 메타데이터를 읽는다."""

from __future__ import annotations

import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class RecordingFileMetadata:
    """녹음 파일에서 코드로 확정할 수 있는 시간 메타데이터."""

    file_modified_at: str | None = None
    duration_ms: int | None = None


def read_recording_file_metadata(audio_path: Path | None) -> RecordingFileMetadata:
    """녹음 파일의 수정 시각과 WAV 길이를 읽는다."""

    if audio_path is None or not audio_path.exists():
        return RecordingFileMetadata()

    file_modified_at = datetime.fromtimestamp(
        audio_path.stat().st_mtime,
        tz=timezone.utc,
    ).isoformat()
    return RecordingFileMetadata(
        file_modified_at=file_modified_at,
        duration_ms=_read_wav_duration_ms(audio_path),
    )


def _read_wav_duration_ms(audio_path: Path) -> int | None:
    try:
        with wave.open(str(audio_path), "rb") as wav_file:
            sample_rate_hz = wav_file.getframerate()
            frame_count = wav_file.getnframes()
    except (OSError, EOFError, wave.Error):
        return None

    if sample_rate_hz <= 0:
        return None
    return int(frame_count / sample_rate_hz * 1000)
