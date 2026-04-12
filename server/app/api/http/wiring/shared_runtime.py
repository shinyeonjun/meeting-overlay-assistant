"""HTTP 계층에서 공통 관련 shared runtime 구성을 담당한다."""
from __future__ import annotations

from server.app.api.http.wiring import audio_runtime, shared_services
from server.app.core.config import settings

# 외부 코드가 기존 private getter 이름에 의존할 수 있어서
# facade 계층에서는 이름만 유지하고 구현은 공용 provider로 위임한다.
get_runtime_monitor_service = shared_services.get_runtime_monitor_service
preload_runtime_services = shared_services.preload_runtime_services
_build_audio_pipeline_service = shared_services.build_audio_pipeline_service
_get_shared_analyzer = shared_services.get_shared_analyzer
_get_shared_speech_to_text_service = shared_services.get_shared_speech_to_text_service
_get_speech_to_text_service = shared_services.get_speech_to_text_service
_create_speech_to_text_service = shared_services.create_speech_to_text_service
_build_stt_build_options = shared_services.build_stt_build_options
_get_shared_audio_preprocessor = shared_services.get_shared_audio_preprocessor
_get_shared_speaker_diarizer = shared_services.get_shared_speaker_diarizer
_get_shared_audio_postprocessing_service = (
    shared_services.get_shared_audio_postprocessing_service
)
_get_shared_speaker_event_projection_service = (
    shared_services.get_shared_speaker_event_projection_service
)
_get_shared_report_refiner = shared_services.get_shared_report_refiner
_get_shared_topic_summarizer = shared_services.get_shared_topic_summarizer
_get_shared_live_event_corrector = shared_services.get_shared_live_event_corrector
_resolve_stt_settings_for_source = shared_services.resolve_stt_settings_for_source


def _build_audio_segmenter(source_policy):
    """오디오 segmenter를 현재 설정으로 구성한다."""

    return audio_runtime.build_audio_segmenter(
        source_policy=source_policy,
        settings=settings,
    )


def _build_audio_content_gate(source_policy):
    """audio content gate를 현재 설정으로 구성한다."""

    return audio_runtime.build_audio_content_gate(
        source_policy=source_policy,
        settings=settings,
    )


def _build_transcription_guard(source_policy):
    """transcription guard를 현재 설정으로 구성한다."""

    return audio_runtime.build_transcription_guard(
        source_policy=source_policy,
        settings=settings,
    )
