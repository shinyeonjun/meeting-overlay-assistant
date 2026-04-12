"""오디오 영역의 wav chunk reader 서비스를 제공한다."""
from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WaveAudioData:
    """WAV 파일에서 읽은 오디오 메타데이터와 PCM 데이터."""

    sample_rate_hz: int
    sample_width_bytes: int
    channels: int
    raw_bytes: bytes


def read_pcm_wave_file(
    path: str | Path,
    *,
    expected_sample_rate_hz: int | None = None,
    expected_sample_width_bytes: int = 2,
    expected_channels: int = 1,
) -> WaveAudioData:
    """PCM WAV 파일을 읽고 기본 포맷을 검증한다."""
    wav_path = Path(path)
    with wave.open(str(wav_path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width_bytes = wav_file.getsampwidth()
        sample_rate_hz = wav_file.getframerate()
        raw_bytes = wav_file.readframes(wav_file.getnframes())

    if channels != expected_channels:
        raise ValueError(
            f"WAV 채널 수가 올바르지 않습니다. expected={expected_channels}, actual={channels}"
        )
    if sample_width_bytes != expected_sample_width_bytes:
        raise ValueError(
            "WAV 샘플 폭이 올바르지 않습니다. "
            f"expected={expected_sample_width_bytes}, actual={sample_width_bytes}"
        )
    if expected_sample_rate_hz is not None and sample_rate_hz != expected_sample_rate_hz:
        raise ValueError(
            "WAV 샘플레이트가 올바르지 않습니다. "
            f"expected={expected_sample_rate_hz}, actual={sample_rate_hz}"
        )

    return WaveAudioData(
        sample_rate_hz=sample_rate_hz,
        sample_width_bytes=sample_width_bytes,
        channels=channels,
        raw_bytes=raw_bytes,
    )


def split_pcm_bytes(
    raw_bytes: bytes,
    *,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
    chunk_duration_ms: int,
) -> list[bytes]:
    """PCM 바이트를 고정 길이 청크 목록으로 나눈다."""
    bytes_per_second = sample_rate_hz * sample_width_bytes * channels
    chunk_size = max(int(bytes_per_second * (chunk_duration_ms / 1000)), sample_width_bytes * channels)
    chunks = [
        raw_bytes[index : index + chunk_size]
        for index in range(0, len(raw_bytes), chunk_size)
        if raw_bytes[index : index + chunk_size]
    ]
    return chunks
