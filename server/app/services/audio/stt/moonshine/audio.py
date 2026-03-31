"""Moonshine 오디오 처리 유틸리티."""

from __future__ import annotations


def pcm16_to_float32_audio(
    *,
    raw_bytes: bytes,
    sample_width_bytes: int,
    channels: int,
    np_module,
):
    """PCM16 바이트를 float32 mono 오디오로 변환한다."""

    if not raw_bytes:
        return np_module.asarray([], dtype=np_module.float32)

    frame_size = max(sample_width_bytes * channels, 1)
    aligned_size = len(raw_bytes) - (len(raw_bytes) % frame_size)
    if aligned_size <= 0:
        return np_module.asarray([], dtype=np_module.float32)

    if sample_width_bytes != 2:
        raise RuntimeError("moonshine backend는 현재 16-bit PCM 입력만 지원합니다.")

    pcm = np_module.frombuffer(raw_bytes[:aligned_size], dtype=np_module.int16).astype(
        np_module.float32
    )
    if channels > 1:
        pcm = pcm.reshape(-1, channels).mean(axis=1)
    return np_module.clip(pcm / 32768.0, -1.0, 1.0)


def compute_rms(audio, *, np_module) -> float:
    """오디오 RMS를 계산한다."""

    if audio.size == 0:
        return 0.0
    return float(
        np_module.sqrt(
            np_module.mean(np_module.square(audio, dtype=np_module.float32))
        )
    )
