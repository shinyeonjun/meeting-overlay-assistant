"""Silero VAD 2단계 검증 세그먼터 테스트."""

from __future__ import annotations

import numpy as np

from backend.app.services.audio.segmentation.silero_vad_segmenter import (
    SileroValidatedSpeechSegmenter,
    SileroVadValidatorConfig,
)
from backend.app.services.audio.segmentation.speech_segmenter import SpeechSegment


class _FakeBaseSegmenter:
    def __init__(self, segments: list[SpeechSegment]) -> None:
        self._segments = segments

    def split(self, chunk: bytes) -> list[SpeechSegment]:
        return self._segments


class TestSileroVadSegmenter:
    def test_silero가_음성으로_판정한_세그먼트만_남긴다(self, monkeypatch):
        segment = SpeechSegment(
            raw_bytes=np.asarray([0, 1000, -1000, 500] * 400, dtype=np.int16).tobytes(),
            start_ms=0,
            end_ms=300,
        )
        validator = SileroValidatedSpeechSegmenter(
            base_segmenter=_FakeBaseSegmenter([segment]),
            config=SileroVadValidatorConfig(min_speech_duration_ms=60),
        )
        monkeypatch.setattr(
            validator,
            "_load_silero_components",
            lambda: (
                lambda audio, model, threshold, sampling_rate: [{"start": 0, "end": 1600}],
                None,
                None,
                None,
                None,
            ),
        )
        monkeypatch.setattr(validator, "_load_silero_model", lambda: object())

        segments = validator.split(b"chunk")

        assert segments == [segment]

    def test_silero가_비음성으로_판정하면_세그먼트를_버린다(self, monkeypatch):
        segment = SpeechSegment(
            raw_bytes=np.asarray([0, 1000, -1000, 500] * 400, dtype=np.int16).tobytes(),
            start_ms=0,
            end_ms=300,
        )
        validator = SileroValidatedSpeechSegmenter(
            base_segmenter=_FakeBaseSegmenter([segment]),
            config=SileroVadValidatorConfig(min_speech_duration_ms=60),
        )
        monkeypatch.setattr(
            validator,
            "_load_silero_components",
            lambda: (
                lambda audio, model, threshold, sampling_rate: [],
                None,
                None,
                None,
                None,
            ),
        )
        monkeypatch.setattr(validator, "_load_silero_model", lambda: object())

        segments = validator.split(b"chunk")

        assert segments == []

