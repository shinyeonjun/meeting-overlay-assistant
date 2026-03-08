"""AudioContentGate 테스트."""

from __future__ import annotations

import math

from backend.app.services.audio.filters.audio_content_gate import (
    AudioContentGate,
    AudioContentGateProfile,
)
from backend.app.services.audio.segmentation.speech_segmenter import SpeechSegment


def _build_segment(samples: list[float], *, sample_rate_hz: int = 16000) -> SpeechSegment:
    pcm_bytes = bytearray()
    for sample in samples:
        clamped = max(min(sample, 0.999), -0.999)
        pcm_value = int(clamped * 32767)
        pcm_bytes.extend(int(pcm_value).to_bytes(2, byteorder="little", signed=True))

    return SpeechSegment(
        raw_bytes=bytes(pcm_bytes),
        start_ms=0,
        end_ms=max(int((len(samples) / sample_rate_hz) * 1000), 1),
    )


def _build_profile(**overrides) -> AudioContentGateProfile:
    base_profile = {
        "enabled": True,
        "sample_rate_hz": 16000,
        "sample_width_bytes": 2,
        "channels": 1,
        "min_rms": 0.01,
        "min_speech_band_ratio": 0.45,
        "min_spectral_flatness": 0.08,
        "min_zero_crossing_rate": 0.015,
    }
    base_profile.update(overrides)
    return AudioContentGateProfile(**base_profile)


def test_무음_세그먼트는_차단한다() -> None:
    gate = AudioContentGate(_build_profile())
    silence_segment = _build_segment([0.0] * 1600)

    assert gate.should_process(silence_segment) is False


def test_음성대역_에너지가_높은_세그먼트는_통과시킨다() -> None:
    gate = AudioContentGate(_build_profile(min_spectral_flatness=0.0))
    samples = [
        (
            0.18 * math.sin(2 * math.pi * 320 * index / 16000)
            + 0.11 * math.sin(2 * math.pi * 760 * index / 16000)
            + 0.07 * math.sin(2 * math.pi * 1480 * index / 16000)
        )
        for index in range(1600)
    ]
    voiced_segment = _build_segment(samples)

    assert gate.should_process(voiced_segment) is True

