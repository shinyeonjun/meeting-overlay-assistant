"""공통 영역의 test dependencies 동작을 검증한다."""
from __future__ import annotations

from dataclasses import replace

from server.app.api.http import dependencies
from server.app.core.config import settings
from server.app.core.runtime_readiness import get_runtime_readiness, reset_runtime_readiness
from server.app.domain.shared.enums import AudioSource
from server.app.services.analysis.correction.live_event_correction_service import (
    NoOpLiveEventCorrectionService,
)


class TestDependencies:
    """Dependencies 동작을 검증한다."""
    def test_shared_analyzer는_같은_인스턴스를_사용한다(self):
        dependencies._get_shared_analyzer.cache_clear()

        first = dependencies._get_shared_analyzer()
        second = dependencies._get_shared_analyzer()

        assert first is second

    def test_shared_stt_service는_source별로_캐시된다(self):
        dependencies._get_shared_speech_to_text_service.cache_clear()

        first = dependencies._get_shared_speech_to_text_service(AudioSource.MIC.value)
        second = dependencies._get_shared_speech_to_text_service(AudioSource.MIC.value)

        assert first is second

    def test_system_audio는_source별_backend_override를_적용한다(self, monkeypatch):
        captured = {}
        original_settings = replace(
            settings,
            stt_backend="faster_whisper_streaming",
            stt_backend_system_audio="hybrid_local_streaming",
        )

        def _fake_create_speech_to_text_service_from_options(options):
            captured["options"] = options
            return object()

        monkeypatch.setattr(
            dependencies,
            "create_speech_to_text_service_from_options",
            _fake_create_speech_to_text_service_from_options,
        )
        monkeypatch.setattr(dependencies, "settings", original_settings)

        dependencies._create_speech_to_text_service(AudioSource.SYSTEM_AUDIO.value)

        assert captured["options"].backend_name == "hybrid_local_streaming"

    def test_mic_and_audio_source는_system_audio_backend_override를_적용한다(self, monkeypatch):
        captured = {}
        original_settings = replace(
            settings,
            stt_backend="faster_whisper_streaming",
            stt_backend_system_audio="hybrid_local_streaming",
        )

        def _fake_create_speech_to_text_service_from_options(options):
            captured["options"] = options
            return object()

        monkeypatch.setattr(
            dependencies,
            "create_speech_to_text_service_from_options",
            _fake_create_speech_to_text_service_from_options,
        )
        monkeypatch.setattr(dependencies, "settings", original_settings)

        dependencies._create_speech_to_text_service(AudioSource.MIC_AND_AUDIO.value)

        assert captured["options"].backend_name == "hybrid_local_streaming"

    def test_stt_생성은_partial_고도화_설정까지_전달한다(self, monkeypatch):
        captured = {}
        original_settings = replace(
            settings,
            stt_backend="faster_whisper_streaming",
            stt_initial_prompt="회의 음성만 인식합니다.",
        )

        def _fake_create_speech_to_text_service_from_options(options):
            captured["options"] = options
            return object()

        monkeypatch.setattr(
            dependencies,
            "create_speech_to_text_service_from_options",
            _fake_create_speech_to_text_service_from_options,
        )
        monkeypatch.setattr(dependencies, "settings", original_settings)

        profile = dependencies.resolve_speech_to_text_profile(original_settings)
        dependencies._create_speech_to_text_service(AudioSource.MIC.value)

        assert captured["options"].backend_name == "faster_whisper_streaming"
        assert captured["options"].initial_prompt == "회의 음성만 인식합니다."
        assert (
            captured["options"].partial_backtrack_tolerance_chars
            == profile.partial_backtrack_tolerance_chars
        )
        assert (
            captured["options"].partial_commit_min_chars_without_boundary
            == profile.partial_commit_min_chars_without_boundary
        )

    def test_preload_runtime_services는_system_audio_override가_있으면_둘다_배열한다(
        self,
        monkeypatch,
    ):
        created_sources: list[str] = []
        preloaded_sources: list[str] = []
        original_settings = replace(
            settings,
            stt_preload_on_startup=True,
            stt_backend="faster_whisper_streaming",
            stt_backend_system_audio="hybrid_local_streaming_sherpa",
        )

        class _FakeService:
            def __init__(self, source: str) -> None:
                self._source = source

            def preload(self) -> None:
                preloaded_sources.append(self._source)

        def _fake_create_speech_to_text_service(source: str):
            created_sources.append(source)
            return _FakeService(source)

        monkeypatch.setattr(dependencies, "settings", original_settings)
        monkeypatch.setattr(
            dependencies,
            "_create_speech_to_text_service",
            _fake_create_speech_to_text_service,
        )

        dependencies.preload_runtime_services()

        assert created_sources == [AudioSource.MIC.value, AudioSource.SYSTEM_AUDIO.value]
        assert preloaded_sources == [AudioSource.MIC.value, AudioSource.SYSTEM_AUDIO.value]

    def test_preload_미구현_backend도_ready로_정리한다(self, monkeypatch):
        created_sources: list[str] = []
        original_settings = replace(
            settings,
            stt_preload_on_startup=True,
            stt_backend="openai_compatible_audio",
            stt_backend_system_audio="",
        )

        def _fake_create_speech_to_text_service(source: str):
            created_sources.append(source)
            return object()

        monkeypatch.setattr(dependencies, "settings", original_settings)
        monkeypatch.setattr(
            dependencies,
            "_create_speech_to_text_service",
            _fake_create_speech_to_text_service,
        )
        reset_runtime_readiness(stt_preload_enabled=True)

        dependencies.preload_runtime_services()

        readiness = get_runtime_readiness()

        assert created_sources == [AudioSource.MIC.value]
        assert readiness["stt_ready"] is True
        assert readiness["preloaded_sources"][AudioSource.MIC.value]["ready"] is True

    def test_live_event_corrector_기본값은_noop이다(self):
        dependencies._get_shared_live_event_corrector.cache_clear()

        service = dependencies._get_shared_live_event_corrector()

        assert isinstance(service, NoOpLiveEventCorrectionService)
