"""Moonshine pseudo-streaming 상태 유틸리티."""

from __future__ import annotations

from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment


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


def trim_buffer(buffer: bytearray, *, max_buffer_bytes: int) -> None:
    """rolling buffer 크기를 제한한다."""

    overflow = len(buffer) - max_buffer_bytes
    if overflow > 0:
        del buffer[:overflow]


def build_preview_segment(
    *,
    raw_bytes: bytes,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
) -> SpeechSegment:
    """preview용 rolling buffer를 SpeechSegment로 감싼다."""

    duration_ms = int(
        len(raw_bytes) / (sample_rate_hz * sample_width_bytes * channels) * 1000
    )
    return SpeechSegment(
        start_ms=0,
        end_ms=max(duration_ms, 1),
        raw_bytes=raw_bytes,
    )


def normalize_text(text: str) -> str:
    """Moonshine preview 중복 제거용 텍스트 정규화."""

    return " ".join(text.casefold().split())
