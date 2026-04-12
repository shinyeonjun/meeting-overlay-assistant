"""오디오 영역의 audio 서비스를 제공한다."""
from __future__ import annotations


def duration_ms_to_bytes(
    *,
    duration_ms: int,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
) -> int:
    """밀리초 구간을 PCM 바이트 길이로 환산한다."""

    bytes_per_second = sample_rate_hz * sample_width_bytes * channels
    return max(int(bytes_per_second * (duration_ms / 1000.0)), 1)


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
        raise RuntimeError(
            "sherpa_onnx_streaming backend는 현재 16-bit PCM 입력만 지원합니다."
        )

    pcm = np_module.frombuffer(raw_bytes[:aligned_size], dtype=np_module.int16).astype(
        np_module.float32
    )
    if channels > 1:
        pcm = pcm.reshape(-1, channels).mean(axis=1)
    return np_module.clip(pcm / 32768.0, -1.0, 1.0)
