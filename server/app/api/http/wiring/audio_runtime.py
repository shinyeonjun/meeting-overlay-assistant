"""HTTP 계층에서 오디오 runtime 조립 진입점을 제공한다.

STT 백엔드 선택, segmenter/content gate/guard 조합, preload 경로를
audio_runtime_builders 하위 모듈에 나눠두고, 상위에서는 이 파일만 통해
runtime 객체를 조립하게 한다.
"""
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
    """오디오 pipeline 서비스를 조립한다.

    실제 분기 로직은 builder 모듈에 두고, 여기서는 final 조립에 필요한
    segmenter, content gate, transcription guard를 일관되게 끼워 넣는다.
    """

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
