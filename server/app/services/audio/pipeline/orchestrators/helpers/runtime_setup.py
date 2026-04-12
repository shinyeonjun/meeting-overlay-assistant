"""오디오 파이프라인 runtime lane 조립 helper."""

from __future__ import annotations

from server.app.services.audio.pipeline.alignment.stream_alignment_manager import (
    StreamAlignmentManager,
)
from server.app.services.audio.pipeline.state.runtime_lane_state import (
    AudioPipelineCoordinationState,
    AudioPipelineFinalLaneState,
    AudioPipelinePreviewLaneState,
)
from server.app.services.audio.segmentation.speech_segmenter import AudioSegmenter
from server.app.services.audio.stt.transcription import (
    SpeechToTextService,
    StreamingSpeechToTextService,
)


def initialize_runtime_lanes(
    service,
    *,
    segmenter: AudioSegmenter,
    speech_to_text_service: SpeechToTextService,
    preview_backpressure_queue_delay_ms: int,
    preview_backpressure_hold_chunks: int,
    segment_grace_match_max_gap_ms: int,
) -> None:
    """preview/final lane 상태와 공용 정렬 상태를 초기화한다."""

    preview_stt_service, final_stt_service = split_runtime_lane_services(
        speech_to_text_service
    )
    service._preview_lane_state = AudioPipelinePreviewLaneState(
        speech_to_text_service=preview_stt_service
    )
    service._final_lane_state = AudioPipelineFinalLaneState(
        segmenter=segmenter,
        speech_to_text_service=final_stt_service,
    )
    service._coordination_state = AudioPipelineCoordinationState(
        alignment_manager=build_alignment_manager(
            preview_backpressure_queue_delay_ms=preview_backpressure_queue_delay_ms,
            preview_backpressure_hold_chunks=preview_backpressure_hold_chunks,
            segment_grace_match_max_gap_ms=segment_grace_match_max_gap_ms,
        )
    )
    # 테스트와 기존 코드가 직접 접근하는 호환 포인트를 유지한다.
    service._alignment_manager = service._coordination_state.alignment_manager


def supports_preview(service) -> bool:
    """현재 STT 서비스가 preview 경로를 지원하는지 반환한다."""

    return service._preview_lane_state.speech_to_text_service is not None


def reset_runtime_streams(service) -> None:
    """preview/final runtime lane 스트림 상태를 초기화한다."""

    preview_service = service._preview_lane_state.speech_to_text_service
    reset_preview_stream = getattr(preview_service, "reset_stream", None)
    if callable(reset_preview_stream):
        reset_preview_stream()

    final_service = service._final_lane_state.speech_to_text_service
    if final_service is preview_service:
        return
    reset_final_stream = getattr(final_service, "reset_stream", None)
    if callable(reset_final_stream):
        reset_final_stream()


def split_runtime_lane_services(
    speech_to_text_service: SpeechToTextService,
) -> tuple[StreamingSpeechToTextService | None, SpeechToTextService]:
    """runtime lane별 STT 서비스를 분리한다."""

    split_services = getattr(
        speech_to_text_service,
        "split_runtime_lane_services",
        None,
    )
    if callable(split_services):
        preview_service, final_service = split_services()
        return preview_service, final_service
    if isinstance(speech_to_text_service, StreamingSpeechToTextService):
        return speech_to_text_service, speech_to_text_service
    return None, speech_to_text_service


def build_alignment_manager(
    *,
    preview_backpressure_queue_delay_ms: int,
    preview_backpressure_hold_chunks: int,
    segment_grace_match_max_gap_ms: int,
) -> StreamAlignmentManager:
    """preview/final 정렬과 backpressure 상태를 관리하는 객체를 만든다."""

    return StreamAlignmentManager(
        preview_backpressure_queue_delay_ms=preview_backpressure_queue_delay_ms,
        preview_backpressure_hold_chunks=preview_backpressure_hold_chunks,
        segment_grace_match_max_gap_ms=segment_grace_match_max_gap_ms,
    )
