"""HTTP 계층에서 공통 관련 audio runtime 구성을 담당한다."""
from __future__ import annotations

from server.app.api.http.wiring.audio_runtime_builders import (
    pipeline,
    preload,
    segmentation,
    stt,
)

preload_runtime_services = preload.preload_runtime_services
create_speech_to_text_service = stt.create_speech_to_text_service
build_stt_build_options = stt.build_stt_build_options
resolve_stt_settings_for_source = stt.resolve_stt_settings_for_source
build_audio_segmenter = segmentation.build_audio_segmenter
build_audio_content_gate = segmentation.build_audio_content_gate
build_transcription_guard = segmentation.build_transcription_guard


def build_audio_pipeline_service(**kwargs):
    """오디오 pipeline 서비스를 조립한다."""

    return pipeline.build_audio_pipeline_service(
        **kwargs,
        build_audio_segmenter=build_audio_segmenter,
        build_audio_content_gate=build_audio_content_gate,
        build_transcription_guard=build_transcription_guard,
    )


def build_text_input_pipeline_service(**kwargs):
    """텍스트 입력용 placeholder pipeline을 조립한다."""

    return pipeline.build_text_input_pipeline_service(
        **kwargs,
        build_transcription_guard=build_transcription_guard,
    )
