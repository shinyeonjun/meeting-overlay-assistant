"""STT 팩토리 테스트."""

from __future__ import annotations

import pytest

from server.app.services.audio.stt import speech_to_text_factory as factory_module
from server.app.services.audio.stt.amd_whisper_npu_speech_to_text_service import (
    AMDWhisperNPUSpeechToTextService,
)
from server.app.services.audio.stt.faster_whisper_speech_to_text_service import (
    FasterWhisperSpeechToTextService,
)
from server.app.services.audio.stt.faster_whisper_streaming_speech_to_text_service import (
    FasterWhisperStreamingSpeechToTextService,
)
from server.app.services.audio.stt.hybrid_streaming_speech_to_text_service import (
    HybridStreamingSpeechToTextService,
)
from server.app.services.audio.stt.moonshine_speech_to_text_service import (
    MoonshineSpeechToTextService,
)
from server.app.services.audio.stt.moonshine_streaming_speech_to_text_service import (
    MoonshineStreamingSpeechToTextService,
)
from server.app.services.audio.stt.openai_compatible_audio_transcription_service import (
    OpenAICompatibleAudioTranscriptionService,
)
from server.app.services.audio.stt.placeholder_speech_to_text_service import (
    PlaceholderSpeechToTextService,
)
from server.app.services.audio.stt.speech_to_text_factory import create_speech_to_text_service
from server.app.services.audio.stt.transcription import TranscriptionResult


class _FakeStreamingService:
    def preview_chunk(self, chunk: bytes) -> list[TranscriptionResult]:
        return [TranscriptionResult(text="partial", confidence=0.7, kind="partial", revision=1)]

    def transcribe(self, segment):  # noqa: ANN001
        return TranscriptionResult(text="", confidence=0.0)

    def reset_stream(self) -> None:
        return None


class _FakeFinalService:
    def transcribe(self, segment):  # noqa: ANN001
        return TranscriptionResult(text="final", confidence=0.9)


class _InvalidFinalService:
    pass


class TestSpeechToTextFactory:
    def test_placeholder_backend를_선택하면_placeholder_service를_반환한다(self):
        service = create_speech_to_text_service("placeholder")
        assert isinstance(service, PlaceholderSpeechToTextService)

    def test_amd_whisper_npu_backend를_선택하면_npu_service를_반환한다(self):
        service = create_speech_to_text_service(
            "amd_whisper_npu",
            model_id="amd/whisper-small-onnx-npu",
        )
        assert isinstance(service, AMDWhisperNPUSpeechToTextService)

    def test_openai_compatible_audio_backend를_선택하면_http_stt_service를_반환한다(self):
        service = create_speech_to_text_service(
            "openai_compatible_audio",
            model_id="whisper-small",
            base_url="http://127.0.0.1:8001/v1/audio",
        )
        assert isinstance(service, OpenAICompatibleAudioTranscriptionService)

    def test_faster_whisper_backend를_선택하면_faster_whisper_service를_반환한다(self):
        service = create_speech_to_text_service(
            "faster_whisper",
            model_id="deepdml/faster-whisper-large-v3-turbo-ct2",
        )
        assert isinstance(service, FasterWhisperSpeechToTextService)

    def test_faster_whisper_streaming_backend를_선택하면_streaming_service를_반환한다(self):
        service = create_speech_to_text_service(
            "faster_whisper_streaming",
            model_id="deepdml/faster-whisper-large-v3-turbo-ct2",
            initial_prompt="회의 음성만 전사한다.",
            partial_backtrack_tolerance_chars=3,
            partial_commit_min_chars_without_boundary=8,
        )
        assert isinstance(service, FasterWhisperStreamingSpeechToTextService)
        assert service._config.initial_prompt is None
        assert service._streaming_config.partial_backtrack_tolerance_chars == 3
        assert service._streaming_config.partial_commit_min_chars_without_boundary == 8

    def test_hybrid_local_streaming_backend는_partial_final_서비스를_조합한다(self, monkeypatch):
        created: list[tuple[str, str]] = []
        original_create = factory_module.create_speech_to_text_service

        def _fake_create(**kwargs):
            backend_name = kwargs["backend_name"]
            if backend_name == "hybrid_local_streaming":
                return original_create(**kwargs)
            created.append((backend_name, kwargs["model_id"]))
            if backend_name == "faster_whisper_streaming":
                return _FakeStreamingService()
            if backend_name == "faster_whisper":
                return _FakeFinalService()
            raise AssertionError(f"unexpected backend: {backend_name}")

        monkeypatch.setattr(factory_module, "create_speech_to_text_service", _fake_create)

        service = factory_module._build_hybrid_local_streaming(
            model_id="shared-model",
            model_path=None,
            language="ko",
            device="auto",
            compute_type="default",
            cpu_threads=0,
            beam_size=1,
            sample_rate_hz=16000,
            sample_width_bytes=2,
            channels=1,
            silence_rms_threshold=0.003,
            partial_buffer_ms=760,
            partial_emit_interval_ms=120,
            partial_min_rms_threshold=0.0025,
            partial_agreement_window=1,
            partial_agreement_min_count=1,
            partial_min_stable_chars=2,
            partial_min_growth_chars=1,
            partial_backtrack_tolerance_chars=4,
            partial_commit_min_chars_without_boundary=2,
            partial_backend_name="faster_whisper_streaming",
            partial_model_id="partial-model",
            partial_model_path=None,
            partial_device="cpu",
            partial_compute_type="int8",
            partial_cpu_threads=2,
            partial_beam_size=1,
            final_backend_name="faster_whisper",
            final_model_id="final-model",
            final_model_path=None,
            final_device="cuda",
            final_compute_type="float16",
            final_cpu_threads=0,
            final_beam_size=3,
        )

        assert isinstance(service, HybridStreamingSpeechToTextService)
        assert created == [
            ("faster_whisper_streaming", "partial-model"),
            ("faster_whisper", "final-model"),
        ]

    def test_hybrid_local_streaming_backend는_final_backend_계약도_검증한다(self, monkeypatch):
        original_create = factory_module.create_speech_to_text_service

        def _fake_create(**kwargs):
            backend_name = kwargs["backend_name"]
            if backend_name == "hybrid_local_streaming":
                return original_create(**kwargs)
            if backend_name == "faster_whisper_streaming":
                return _FakeStreamingService()
            if backend_name == "faster_whisper":
                return _InvalidFinalService()
            raise AssertionError(f"unexpected backend: {backend_name}")

        monkeypatch.setattr(factory_module, "create_speech_to_text_service", _fake_create)

        with pytest.raises(TypeError, match="final backend"):
            factory_module._build_hybrid_local_streaming(
                model_id="shared-model",
                model_path=None,
                language="ko",
                device="auto",
                compute_type="default",
                cpu_threads=0,
                beam_size=1,
                sample_rate_hz=16000,
                sample_width_bytes=2,
                channels=1,
                silence_rms_threshold=0.003,
                partial_buffer_ms=760,
                partial_emit_interval_ms=120,
                partial_min_rms_threshold=0.0025,
                partial_agreement_window=1,
                partial_agreement_min_count=1,
                partial_min_stable_chars=2,
                partial_min_growth_chars=1,
                partial_backtrack_tolerance_chars=4,
                partial_commit_min_chars_without_boundary=2,
                partial_backend_name="faster_whisper_streaming",
                partial_model_id="partial-model",
                partial_model_path=None,
                partial_device="cpu",
                partial_compute_type="int8",
                partial_cpu_threads=2,
                partial_beam_size=1,
                final_backend_name="faster_whisper",
                final_model_id="final-model",
                final_model_path=None,
                final_device="cuda",
                final_compute_type="float16",
                final_cpu_threads=0,
                final_beam_size=3,
            )

    def test_moonshine_backend를_선택하면_moonshine_service를_반환한다(self):
        service = create_speech_to_text_service(
            "moonshine",
            model_id="moonshine/base",
        )
        assert isinstance(service, MoonshineSpeechToTextService)

    def test_moonshine_streaming_backend를_선택하면_streaming_service를_반환한다(self):
        service = create_speech_to_text_service(
            "moonshine_streaming",
            model_id="moonshine/base",
        )
        assert isinstance(service, MoonshineStreamingSpeechToTextService)

    def test_지원하지_않는_backend를_선택하면_예외가_발생한다(self):
        with pytest.raises(ValueError):
            create_speech_to_text_service("unknown")

