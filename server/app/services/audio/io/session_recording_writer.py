"""오디오 영역의 session recording writer 서비스를 제공한다."""
from __future__ import annotations

import wave
from pathlib import Path


class SessionRecordingWriter:
    """세션별 raw PCM chunk를 WAV 파일로 누적 저장한다."""

    def __init__(
        self,
        *,
        output_path: Path,
        sample_rate_hz: int,
        sample_width_bytes: int,
        channels: int,
    ) -> None:
        self._output_path = output_path
        self._sample_rate_hz = sample_rate_hz
        self._sample_width_bytes = sample_width_bytes
        self._channels = channels
        self._wave_file: wave.Wave_write | None = None

    @property
    def output_path(self) -> Path:
        return self._output_path

    def append_chunk(self, chunk: bytes) -> None:
        """PCM chunk를 WAV 파일에 누적 저장한다."""

        if not chunk:
            return
        if self._wave_file is None:
            self._open()
        assert self._wave_file is not None
        self._wave_file.writeframes(chunk)

    def close(self) -> None:
        """열린 WAV 파일을 닫는다."""

        if self._wave_file is None:
            return
        self._wave_file.close()
        self._wave_file = None

    def _open(self) -> None:
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        wave_file = wave.open(str(self._output_path), "wb")
        wave_file.setnchannels(self._channels)
        wave_file.setsampwidth(self._sample_width_bytes)
        wave_file.setframerate(self._sample_rate_hz)
        self._wave_file = wave_file
