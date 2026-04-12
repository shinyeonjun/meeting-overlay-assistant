"""하이브리드 STT 서비스 테스트."""

from __future__ import annotations

from server.app.services.audio.stt.hybrid_streaming_speech_to_text_service import (
    HybridStreamingConfig,
    HybridStreamingSpeechToTextService,
)
from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.transcription import TranscriptionResult


class _FakePartialService:
    def __init__(self) -> None:
        self.reset_called = False
        self.preload_called = False

    def preview_chunk(self, chunk: bytes) -> list[TranscriptionResult]:
        return [TranscriptionResult(text="안녕", confidence=0.7, kind="partial", revision=1)]

    def preload(self) -> None:
        self.preload_called = True

    def reset_stream(self) -> None:
        self.reset_called = True


class _FakeFinalService:
    def __init__(self) -> None:
        self.segments: list[SpeechSegment] = []
        self.preload_called = False
        self.reset_called = False

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        self.segments.append(segment)
        return TranscriptionResult(text="안녕하세요", confidence=0.91)

    def preload(self) -> None:
        self.preload_called = True

    def reset_stream(self) -> None:
        self.reset_called = True


class TestHybridStreamingSpeechToTextService:
    def test_preview_chunk는_partial_엔진에_위임한다(self):
        service = HybridStreamingSpeechToTextService(
            config=HybridStreamingConfig(),
            partial_service=_FakePartialService(),
            final_service=_FakeFinalService(),
        )

        result = service.preview_chunk(b"chunk")

        assert result[0].text == "안녕"
        assert result[0].kind == "partial"

    def test_transcribe는_final_엔진에_위임하고_partial_stream을_reset한다(self):
        partial_service = _FakePartialService()
        final_service = _FakeFinalService()
        service = HybridStreamingSpeechToTextService(
            config=HybridStreamingConfig(reset_partial_stream_on_final=True),
            partial_service=partial_service,
            final_service=final_service,
        )
        segment = SpeechSegment(raw_bytes=b"audio", start_ms=0, end_ms=1000)

        result = service.transcribe(segment)

        assert result.text == "안녕하세요"
        assert final_service.segments == [segment]
        assert partial_service.reset_called is True

    def test_preload는_partial과_final_엔진을_함께_예열한다(self):
        partial_service = _FakePartialService()
        final_service = _FakeFinalService()
        service = HybridStreamingSpeechToTextService(
            config=HybridStreamingConfig(),
            partial_service=partial_service,
            final_service=final_service,
        )

        service.preload()

        assert partial_service.preload_called is True
        assert final_service.preload_called is True

    def test_runtime_lane_services를_분리해도_final_lane은_final_엔진을_사용한다(self):
        partial_service = _FakePartialService()
        final_service = _FakeFinalService()
        service = HybridStreamingSpeechToTextService(
            config=HybridStreamingConfig(reset_partial_stream_on_final=True),
            partial_service=partial_service,
            final_service=final_service,
        )
        segment = SpeechSegment(raw_bytes=b"audio", start_ms=0, end_ms=1000)

        preview_service, final_lane_service = service.split_runtime_lane_services()
        result = final_lane_service.transcribe(segment)
        final_lane_service.reset_stream()

        assert preview_service is partial_service
        assert result.text == "안녕하세요"
        assert final_service.segments == [segment]
        assert partial_service.reset_called is True
        assert final_service.reset_called is True

