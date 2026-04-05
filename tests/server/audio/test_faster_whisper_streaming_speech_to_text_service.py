"""faster-whisper pseudo-streaming STT 테스트."""

from __future__ import annotations

import numpy as np

from server.app.services.audio.stt.faster_whisper_streaming_speech_to_text_service import (
    FasterWhisperStreamingConfig,
    FasterWhisperStreamingSpeechToTextService,
)
from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.transcription import TranscriptionResult


class TestFasterWhisperStreamingSpeechToTextService:
    """faster-whisper pseudo-streaming 동작을 검증한다."""

    @staticmethod
    def _chunk() -> bytes:
        return np.asarray([0, 8000, -8000, 4000] * 800, dtype=np.int16).tobytes()

    @staticmethod
    def _service(**overrides: object) -> FasterWhisperStreamingSpeechToTextService:
        config_kwargs = {
            "model_id": "deepdml/faster-whisper-large-v3-turbo-ct2",
            "partial_buffer_ms": 200,
            "partial_emit_interval_ms": 100,
            "partial_min_rms_threshold": 0.001,
            "partial_agreement_window": 2,
            "partial_agreement_min_count": 2,
            "partial_min_stable_chars": 4,
            "partial_min_growth_chars": 2,
            "partial_commit_min_chars_without_boundary": 4,
        }
        config_kwargs.update(overrides)
        config = FasterWhisperStreamingConfig(**config_kwargs)
        return FasterWhisperStreamingSpeechToTextService(config)

    def test_korean_text_without_spaces_emits_partial(self, monkeypatch) -> None:
        service = self._service()

        monkeypatch.setattr(
            FasterWhisperStreamingSpeechToTextService,
            "_transcribe_preview_segment",
            lambda self, segment: TranscriptionResult(
                text="\uc548\ub155\ud558\uc138\uc694\uc5ec\ub7ec\ubd84",
                confidence=0.88,
                kind="final",
            ),
        )

        first = service.preview_chunk(self._chunk())
        second = service.preview_chunk(self._chunk())

        assert first == []
        assert len(second) == 1
        assert second[0].kind == "partial"
        assert second[0].revision == 1
        assert second[0].text == "\uc548\ub155\ud558\uc138\uc694\uc5ec\ub7ec\ubd84"

    def test_agreement_min_count_1이면_첫_chunk에서도_partial을_낸다(self, monkeypatch) -> None:
        service = self._service(
            partial_agreement_window=1,
            partial_agreement_min_count=1,
            partial_min_stable_chars=2,
            partial_commit_min_chars_without_boundary=2,
        )

        monkeypatch.setattr(
            FasterWhisperStreamingSpeechToTextService,
            "_transcribe_preview_segment",
            lambda self, segment: TranscriptionResult(
                text="\uc548\ub155\ud558\uc138\uc694",
                confidence=0.88,
                kind="final",
            ),
        )

        previews = service.preview_chunk(self._chunk())

        assert len(previews) == 1
        assert previews[0].kind == "partial"
        assert previews[0].revision == 1
        assert previews[0].text == "\uc548\ub155\ud558\uc138\uc694"

    def test_same_partial_is_not_re_emitted(self, monkeypatch) -> None:
        service = self._service()

        monkeypatch.setattr(
            FasterWhisperStreamingSpeechToTextService,
            "_transcribe_preview_segment",
            lambda self, segment: TranscriptionResult(
                text="\uc548\ub155\ud558\uc138\uc694 \uc5ec\ub7ec\ubd84",
                confidence=0.88,
                kind="final",
            ),
        )

        service.preview_chunk(self._chunk())
        second = service.preview_chunk(self._chunk())
        third = service.preview_chunk(self._chunk())

        assert len(second) == 1
        assert third == []

    def test_punctuation_variation_does_not_freeze_partial(self, monkeypatch) -> None:
        service = self._service(partial_agreement_window=2, partial_agreement_min_count=2)
        responses = iter(
            [
                "\uc548\ub155\ud558\uc138\uc694 \uc624\ub298",
                "\uc548\ub155\ud558\uc138\uc694, \uc624\ub298",
            ]
        )

        monkeypatch.setattr(
            FasterWhisperStreamingSpeechToTextService,
            "_transcribe_preview_segment",
            lambda self, segment: TranscriptionResult(
                text=next(responses),
                confidence=0.9,
                kind="final",
            ),
        )

        service.preview_chunk(self._chunk())
        previews = service.preview_chunk(self._chunk())

        assert len(previews) == 1
        assert previews[0].text == "\uc548\ub155\ud558\uc138\uc694, \uc624\ub298"

    def test_small_backtrack_keeps_previous_partial(self, monkeypatch) -> None:
        service = self._service(
            partial_agreement_window=2,
            partial_agreement_min_count=2,
            partial_backtrack_tolerance_chars=2,
        )

        service._last_stable_preview = "\uc548\ub155\ud558\uc138\uc694\uc5ec\ub7ec\ubd84"
        service._last_emitted_preview = "\uc548\ub155\ud558\uc138\uc694"

        responses = iter(
            [
                "\uc548\ub155\ud558\uc138\uc694\uc5ec\ub7ec\ubd84",
                "\uc548\ub155\ud558\uc138\uc694\uc5ec\ub7ec",
            ]
        )

        monkeypatch.setattr(
            FasterWhisperStreamingSpeechToTextService,
            "_transcribe_preview_segment",
            lambda self, segment: TranscriptionResult(
                text=next(responses),
                confidence=0.9,
                kind="final",
            ),
        )

        service.preview_chunk(self._chunk())
        previews = service.preview_chunk(self._chunk())

        assert len(previews) == 1
        assert previews[0].text == "\uc548\ub155\ud558\uc138\uc694\uc5ec\ub7ec\ubd84"

    def test_final_transcribe_resets_stream_state(self, monkeypatch) -> None:
        service = self._service()
        chunk = self._chunk()
        service._buffer.extend(chunk)
        service._bytes_since_emit = len(chunk)
        service._preview_revision = 3
        service._last_emitted_preview = "\uc774\uc804 partial"
        service._last_stable_preview = "\uc774\uc804 partial"
        service._preview_history.extend(["\uc774\uc804 partial", "\uc774\uc804 partial"])

        monkeypatch.setattr(
            FasterWhisperStreamingSpeechToTextService.__mro__[1],
            "transcribe",
            lambda self, segment: TranscriptionResult(
                text="\ucd5c\uc885 \ubb38\uc7a5",
                confidence=0.92,
                kind="final",
                no_speech_prob=0.42,
            ),
        )

        result = service.transcribe(
            SpeechSegment(
                start_ms=0,
                end_ms=1000,
                raw_bytes=chunk,
            )
        )

        assert result.kind == "final"
        assert result.text == "\ucd5c\uc885 \ubb38\uc7a5"
        assert result.no_speech_prob == 0.42
        assert service._buffer == bytearray()
        assert service._bytes_since_emit == 0
        assert service._preview_revision == 0
        assert service._last_emitted_preview == ""
        assert service._last_stable_preview == ""
        assert list(service._preview_history) == []

