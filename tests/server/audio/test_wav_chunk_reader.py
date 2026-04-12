"""오디오 영역의 test wav chunk reader 동작을 검증한다."""
from __future__ import annotations

import wave
from pathlib import Path

import pytest

from server.app.services.audio.io.wav_chunk_reader import read_pcm_wave_file, split_pcm_bytes


def _write_test_wav(
    path: Path,
    *,
    sample_rate_hz: int = 16000,
    sample_width_bytes: int = 2,
    channels: int = 1,
    raw_bytes: bytes = b"\x00\x00" * 160,
) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width_bytes)
        wav_file.setframerate(sample_rate_hz)
        wav_file.writeframes(raw_bytes)


class TestWavChunkReader:
    """WAV 입력 검증과 청크 분할을 확인한다."""

    def test_pcm_wav를_읽으면_메타데이터와_raw_bytes를_반환한다(self, tmp_path: Path):
        wav_path = tmp_path / "sample.wav"
        raw_bytes = b"\x01\x00\x02\x00" * 10
        _write_test_wav(wav_path, raw_bytes=raw_bytes)

        audio = read_pcm_wave_file(wav_path, expected_sample_rate_hz=16000)

        assert audio.sample_rate_hz == 16000
        assert audio.sample_width_bytes == 2
        assert audio.channels == 1
        assert audio.raw_bytes == raw_bytes

    def test_포맷이_다르면_예외를_발생시킨다(self, tmp_path: Path):
        wav_path = tmp_path / "stereo.wav"
        _write_test_wav(wav_path, channels=2)

        with pytest.raises(ValueError):
            read_pcm_wave_file(wav_path, expected_sample_rate_hz=16000, expected_channels=1)

    def test_pcm_bytes를_지정한_길이로_분할한다(self):
        raw_bytes = b"\x00\x01" * 16000

        chunks = split_pcm_bytes(
            raw_bytes,
            sample_rate_hz=16000,
            sample_width_bytes=2,
            channels=1,
            chunk_duration_ms=250,
        )

        assert len(chunks) == 4
        assert all(len(chunk) == 8000 for chunk in chunks)

