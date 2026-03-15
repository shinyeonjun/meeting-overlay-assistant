"""faster-whisper STT 서비스 테스트."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from server.app.services.audio.stt.faster_whisper_speech_to_text_service import (
    FasterWhisperConfig,
    FasterWhisperSpeechToTextService,
)
from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment


class _FakeWhisperModel:
    def __init__(self, model_name_or_path: str, **kwargs) -> None:
        self.model_name_or_path = model_name_or_path
        self.kwargs = kwargs
        self.last_initial_prompt = None

    def transcribe(
        self,
        audio,
        language: str | None,
        beam_size: int,
        vad_filter: bool,
        initial_prompt: str | None = None,
    ):
        self.last_initial_prompt = initial_prompt
        segments = [
            SimpleNamespace(text="안녕하세요", avg_logprob=-0.1, no_speech_prob=0.12),
            SimpleNamespace(text="회의를 시작하겠습니다", avg_logprob=-0.2, no_speech_prob=0.08),
        ]
        info = SimpleNamespace(
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            initial_prompt=initial_prompt,
        )
        return segments, info


class TestFasterWhisperSpeechToTextService:
    """faster-whisper STT 서비스 동작을 검증한다."""

    def setup_method(self) -> None:
        FasterWhisperSpeechToTextService.clear_model_cache()

    def test_전사_결과를_텍스트와_confidence로_변환한다(self, monkeypatch):
        monkeypatch.setattr(
            FasterWhisperSpeechToTextService,
            "_load_model_class",
            staticmethod(lambda: _FakeWhisperModel),
        )
        service = FasterWhisperSpeechToTextService(
            FasterWhisperConfig(
                model_id="deepdml/faster-whisper-large-v3-turbo-ct2",
                beam_size=2,
            )
        )
        segment = SpeechSegment(
            start_ms=0,
            end_ms=1000,
            raw_bytes=np.asarray([0, 12000, -12000, 4000], dtype=np.int16).tobytes(),
        )

        result = service.transcribe(segment)

        assert result.text == "안녕하세요 회의를 시작하겠습니다"
        assert 0.0 < result.confidence <= 1.0
        assert result.no_speech_prob == 0.12

    def test_빈_initial_prompt는_모델에_전달하지_않는다(self, monkeypatch):
        monkeypatch.setattr(
            FasterWhisperSpeechToTextService,
            "_load_model_class",
            staticmethod(lambda: _FakeWhisperModel),
        )
        service = FasterWhisperSpeechToTextService(
            FasterWhisperConfig(
                model_id="deepdml/faster-whisper-large-v3-turbo-ct2",
                initial_prompt="",
            )
        )
        segment = SpeechSegment(
            start_ms=0,
            end_ms=1000,
            raw_bytes=np.asarray([0, 12000, -12000, 4000], dtype=np.int16).tobytes(),
        )

        service.transcribe(segment)

        assert service._model.last_initial_prompt is None

    def test_무음_구간은_빈_전사로_처리한다(self, monkeypatch):
        monkeypatch.setattr(
            FasterWhisperSpeechToTextService,
            "_load_model_class",
            staticmethod(lambda: _FakeWhisperModel),
        )
        service = FasterWhisperSpeechToTextService(
            FasterWhisperConfig(
                model_id="deepdml/faster-whisper-large-v3-turbo-ct2",
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

    def test_캐시된_로컬_모델_경로를_우선_사용한다(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            FasterWhisperSpeechToTextService,
            "_load_model_class",
            staticmethod(lambda: _FakeWhisperModel),
        )
        monkeypatch.setattr(
            FasterWhisperSpeechToTextService,
            "_resolve_cached_model_path",
            lambda self: tmp_path,
        )
        service = FasterWhisperSpeechToTextService(
            FasterWhisperConfig(
                model_id="deepdml/faster-whisper-large-v3-turbo-ct2",
            )
        )

        model = service._get_model()

        assert model.model_name_or_path == str(tmp_path)

    def test_preload는_로컬_아티팩트가_없으면_예외없이_건너뛴다(self, monkeypatch):
        monkeypatch.setattr(
            FasterWhisperSpeechToTextService,
            "_resolve_explicit_model_path",
            lambda self: None,
        )
        monkeypatch.setattr(
            FasterWhisperSpeechToTextService,
            "_resolve_cached_model_path",
            lambda self: None,
        )
        service = FasterWhisperSpeechToTextService(
            FasterWhisperConfig(model_id="deepdml/faster-whisper-large-v3-turbo-ct2")
        )

        service.preload()

    def test_서비스_인스턴스가_달라도_모델_객체를_재사용한다(self, monkeypatch):
        load_calls: list[str] = []

        class _CountingFakeWhisperModel(_FakeWhisperModel):
            def __init__(self, model_name_or_path: str, **kwargs) -> None:
                load_calls.append(model_name_or_path)
                super().__init__(model_name_or_path, **kwargs)

        monkeypatch.setattr(
            FasterWhisperSpeechToTextService,
            "_load_model_class",
            staticmethod(lambda: _CountingFakeWhisperModel),
        )
        first = FasterWhisperSpeechToTextService(
            FasterWhisperConfig(model_id="deepdml/faster-whisper-large-v3-turbo-ct2")
        )
        second = FasterWhisperSpeechToTextService(
            FasterWhisperConfig(model_id="deepdml/faster-whisper-large-v3-turbo-ct2")
        )

        first_model = first._get_model()
        second_model = second._get_model()

        assert first_model is second_model
        assert len(load_calls) == 1

