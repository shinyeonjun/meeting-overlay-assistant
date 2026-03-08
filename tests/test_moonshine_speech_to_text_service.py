"""Moonshine STT 서비스 테스트."""

from __future__ import annotations

import numpy as np

from backend.app.services.audio.stt.moonshine_speech_to_text_service import (
    MoonshineConfig,
    MoonshineSpeechToTextService,
)
from backend.app.services.audio.segmentation.speech_segmenter import SpeechSegment


class TestMoonshineSpeechToTextService:
    """Moonshine STT 서비스 동작을 검증한다."""

    def test_전사_결과를_문자열로_반환한다(self, monkeypatch):
        monkeypatch.setattr(
            MoonshineSpeechToTextService,
            "_run_transcribe",
            staticmethod(lambda **kwargs: ["안녕하세요", "회의를 시작합니다"]),
        )
        service = MoonshineSpeechToTextService(
            MoonshineConfig(
                model_id="moonshine/base",
            )
        )
        segment = SpeechSegment(
            start_ms=0,
            end_ms=1000,
            raw_bytes=np.asarray([0, 10000, -10000, 5000], dtype=np.int16).tobytes(),
        )

        result = service.transcribe(segment)

        assert result.text == "안녕하세요 회의를 시작합니다"
        assert result.confidence == 0.8

    def test_무음_구간은_빈_전사로_처리한다(self):
        service = MoonshineSpeechToTextService(
            MoonshineConfig(
                model_id="moonshine/base",
                silence_rms_threshold=0.01,
            )
        )
        segment = SpeechSegment(
            start_ms=0,
            end_ms=1000,
            raw_bytes=np.zeros(16000, dtype=np.int16).tobytes(),
        )

        result = service.transcribe(segment)

        assert result.text == ""
        assert result.confidence == 0.0

