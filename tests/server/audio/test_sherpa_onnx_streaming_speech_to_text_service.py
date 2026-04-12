"""오디오 영역의 test sherpa onnx streaming speech to text service 동작을 검증한다."""
from __future__ import annotations

from pathlib import Path

from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.sherpa_onnx_streaming_speech_to_text_service import (
    SherpaOnnxStreamingConfig,
    SherpaOnnxStreamingSpeechToTextService,
)


class _FakeStream:
    def __init__(self) -> None:
        self.audio_inputs: list[object] = []
        self.finished = False
        self.text = ""

    def accept_waveform(self, sample_rate: int, audio) -> None:  # noqa: ANN001
        self.audio_inputs.append((sample_rate, audio))

    def input_finished(self) -> None:
        self.finished = True


class _FakeRecognizer:
    def __init__(self) -> None:
        self.streams: list[_FakeStream] = []
        self.next_texts = ["안", "안녕", "안녕하세요"]

    def create_stream(self) -> _FakeStream:
        stream = _FakeStream()
        self.streams.append(stream)
        return stream

    def is_ready(self, stream: _FakeStream) -> bool:
        return bool(stream.audio_inputs)

    def decode_stream(self, stream: _FakeStream) -> None:
        if self.next_texts:
            stream.text = self.next_texts.pop(0)
        stream.audio_inputs.clear()

    def get_result(self, stream: _FakeStream) -> str:
        return stream.text


class TestSherpaOnnxStreamingSpeechToTextService:
    """SherpaOnnxStreamingSpeechToTextService 동작을 검증한다."""
    _chunk = b"\x00\x10" * 64

    @staticmethod
    def _config(**overrides: object) -> SherpaOnnxStreamingConfig:
        config_kwargs = {
            "model_path": Path("D:/caps/server/models/stt/sherpa"),
            "partial_emit_interval_ms": 1,
            "partial_agreement_window": 2,
            "partial_agreement_min_count": 2,
            "partial_min_stable_chars": 2,
            "partial_min_growth_chars": 1,
            "partial_backtrack_tolerance_chars": 2,
            "partial_commit_min_chars_without_boundary": 2,
        }
        config_kwargs.update(overrides)
        return SherpaOnnxStreamingConfig(**config_kwargs)

    def test_preview_chunk는_preview뒤에_live_final을_추가로_내보낸다(self, monkeypatch):
        fake_recognizer = _FakeRecognizer()
        fake_recognizer.next_texts = ["안녕", "안녕하세요"]
        monkeypatch.setattr(
            SherpaOnnxStreamingSpeechToTextService,
            "_create_recognizer",
            classmethod(lambda cls, config: fake_recognizer),
        )
        service = SherpaOnnxStreamingSpeechToTextService(self._config())

        first = service.preview_chunk(self._chunk)
        second = service.preview_chunk(self._chunk)

        assert len(first) == 1
        assert first[0].kind == "preview"
        assert first[0].text == "안녕"
        assert second[0].kind == "preview"
        assert second[-1].kind == "live_final"
        assert second[-1].text == "안녕"

    def test_preview_chunk는_작은_backtrack이면_live_final은_유지하고_preview만_갱신한다(self, monkeypatch):
        fake_recognizer = _FakeRecognizer()
        fake_recognizer.next_texts = ["안녕하세요여러분", "안녕하세요여러"]
        monkeypatch.setattr(
            SherpaOnnxStreamingSpeechToTextService,
            "_create_recognizer",
            classmethod(lambda cls, config: fake_recognizer),
        )
        service = SherpaOnnxStreamingSpeechToTextService(
            self._config(
                partial_agreement_window=1,
                partial_agreement_min_count=1,
            )
        )

        first = service.preview_chunk(self._chunk)
        second = service.preview_chunk(self._chunk)

        assert first[0].text == "안녕하세요여러분"
        assert first[-1].kind == "live_final"
        assert len(second) == 1
        assert second[0].kind == "preview"
        assert second[0].text == "안녕하세요여러"

    def test_transcribe는_새_stream으로_final을_생성한다(self, monkeypatch):
        fake_recognizer = _FakeRecognizer()
        fake_recognizer.next_texts = ["최종 문장"]
        monkeypatch.setattr(
            SherpaOnnxStreamingSpeechToTextService,
            "_create_recognizer",
            classmethod(lambda cls, config: fake_recognizer),
        )
        service = SherpaOnnxStreamingSpeechToTextService(self._config())

        result = service.transcribe(SpeechSegment(raw_bytes=self._chunk, start_ms=0, end_ms=100))

        assert result.text == "최종 문장"
        assert result.kind == "final"

    def test_reset_stream은_revision과_partial_state를_초기화한다(self, monkeypatch):
        fake_recognizer = _FakeRecognizer()
        monkeypatch.setattr(
            SherpaOnnxStreamingSpeechToTextService,
            "_create_recognizer",
            classmethod(lambda cls, config: fake_recognizer),
        )
        service = SherpaOnnxStreamingSpeechToTextService(
            self._config(
                partial_agreement_window=1,
                partial_agreement_min_count=1,
            )
        )
        service.preview_chunk(self._chunk)

        service.reset_stream()

        assert service._preview_revision == 0
        assert service._last_partial_text == ""
        assert service._last_emitted_preview == ""
        assert service._last_stable_preview == ""
        assert service._bytes_since_emit == 0
        assert list(service._preview_history) == []
