"""Moonshine streaming STT 테스트."""

from __future__ import annotations

import numpy as np

from server.app.services.audio.stt.moonshine_streaming_speech_to_text_service import (
    MoonshineStreamingConfig,
    MoonshineStreamingSpeechToTextService,
)
from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.transcription import TranscriptionResult


class TestMoonshineStreamingSpeechToTextService:
    """Moonshine streaming STT 동작을 검증한다."""

    @staticmethod
    def _chunk() -> bytes:
        return np.asarray([0, 8000, -8000, 4000] * 800, dtype=np.int16).tobytes()

    def test_emit_interval이_충족되면_partial_transcript를_반환한다(self, monkeypatch):
        service = MoonshineStreamingSpeechToTextService(
            MoonshineStreamingConfig(
                model_id="moonshine/base",
                partial_buffer_ms=200,
                partial_emit_interval_ms=100,
                partial_min_rms_threshold=0.001,
            )
        )
        monkeypatch.setattr(
            MoonshineStreamingSpeechToTextService,
            "_transcribe_preview_segment",
            lambda self, segment: TranscriptionResult(
                text="안녕하세요",
                confidence=0.88,
                kind="final",
            ),
        )

        previews = service.preview_chunk(self._chunk())

        assert len(previews) == 1
        assert previews[0].kind == "partial"
        assert previews[0].revision == 1
        assert previews[0].text == "안녕하세요"

    def test_partial_text가_동일하면_중복_partial을_생성하지_않는다(self, monkeypatch):
        service = MoonshineStreamingSpeechToTextService(
            MoonshineStreamingConfig(
                model_id="moonshine/base",
                partial_buffer_ms=200,
                partial_emit_interval_ms=100,
                partial_min_rms_threshold=0.001,
            )
        )
        monkeypatch.setattr(
            MoonshineStreamingSpeechToTextService,
            "_transcribe_preview_segment",
            lambda self, segment: TranscriptionResult(
                text="안녕하세요",
                confidence=0.88,
                kind="final",
            ),
        )

        first = service.preview_chunk(self._chunk())
        second = service.preview_chunk(self._chunk())

        assert len(first) == 1
        assert second == []

    def test_final_transcribe_후에는_stream_state를_초기화한다(self, monkeypatch):
        service = MoonshineStreamingSpeechToTextService(
            MoonshineStreamingConfig(
                model_id="moonshine/base",
                partial_buffer_ms=200,
                partial_emit_interval_ms=100,
                partial_min_rms_threshold=0.001,
            )
        )
        chunk = self._chunk()
        service._buffer.extend(chunk)
        service._bytes_since_emit = len(chunk)
        service._preview_revision = 3
        service._last_preview_text = "이전 partial"

        monkeypatch.setattr(
            MoonshineStreamingSpeechToTextService.__mro__[1],
            "transcribe",
            lambda self, segment: TranscriptionResult(text="최종 문장", confidence=0.92),
        )

        result = service.transcribe(
            SpeechSegment(
                start_ms=0,
                end_ms=1000,
                raw_bytes=chunk,
            )
        )

        assert result.kind == "final"
        assert service._buffer == bytearray()
        assert service._preview_revision == 0
        assert service._last_preview_text == ""

