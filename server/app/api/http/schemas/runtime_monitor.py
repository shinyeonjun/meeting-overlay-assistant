"""HTTP 계층에서 공통 관련 runtime monitor 구성을 담당한다."""
from pydantic import BaseModel


class RuntimeMonitorReadinessResponse(BaseModel):
    """현재 런타임 readiness 스냅샷."""

    backend_ready: bool
    warming: bool
    stt_ready: bool
    stt_preload_enabled: bool
    preloaded_sources: dict[str, object]


class RuntimeMonitorAudioPipelineResponse(BaseModel):
    """실시간 오디오 파이프라인 지표."""

    recent_final_count: int
    recent_utterance_count: int
    recent_event_count: int
    average_queue_delay_ms: float | None = None
    max_queue_delay_ms: int | None = None
    late_final_count: int
    backpressure_count: int
    filtered_count: int
    error_count: int
    matched_count: int
    grace_matched_count: int
    standalone_count: int
    standalone_ratio: float
    live_final_compare_count: int
    live_final_exact_match_count: int
    live_final_changed_count: int
    live_final_change_ratio: float
    live_final_average_similarity: float | None = None
    live_final_average_delay_ms: float | None = None
    preview_candidate_count: int
    preview_candidate_preview_count: int
    preview_candidate_live_final_count: int
    preview_first_attempted_anchor_at_ms: int | None = None
    preview_timeline_anchor_at_ms: int | None = None
    preview_first_productive_gap_ms: int | None = None
    preview_empty_cycles_before_first_candidate_count: int
    preview_first_ready_at_ms: int | None = None
    preview_first_job_started_at_ms: int | None = None
    preview_first_picked_at_ms: int | None = None
    preview_first_sherpa_non_empty_at_ms: int | None = None
    preview_first_candidate_at_ms: int | None = None
    preview_first_ready_relative_ms: int | None = None
    preview_first_job_started_relative_ms: int | None = None
    preview_first_picked_relative_ms: int | None = None
    preview_first_sherpa_non_empty_relative_ms: int | None = None
    preview_first_candidate_relative_ms: int | None = None
    preview_first_ready_pending_final_chunk_count: int | None = None
    preview_first_ready_busy_worker_count: int | None = None
    preview_first_picked_pending_final_chunk_count: int | None = None
    preview_first_picked_busy_worker_count: int | None = None
    preview_notify_skipped_busy_count: int
    preview_notify_skipped_preferred_final_count: int
    preview_first_busy_skip_at_ms: int | None = None
    preview_first_preferred_final_skip_at_ms: int | None = None
    preview_first_busy_skip_relative_ms: int | None = None
    preview_first_preferred_final_skip_relative_ms: int | None = None
    preview_first_busy_skip_pending_final_chunk_count: int | None = None
    preview_first_busy_skip_has_pending_preview_chunk: bool | None = None
    preview_first_busy_skip_busy_worker_count: int | None = None
    preview_first_busy_skip_busy_job_kind: str | None = None
    preview_first_preferred_final_skip_pending_final_chunk_count: int | None = None
    preview_first_preferred_final_skip_has_pending_preview_chunk: bool | None = None
    preview_first_preferred_final_skip_busy_worker_count: int | None = None
    preview_first_preferred_final_skip_busy_job_kind: str | None = None
    preview_emitted_count: int
    preview_emitted_preview_count: int
    preview_emitted_live_final_count: int
    preview_guard_rejected_count: int
    preview_length_rejected_count: int
    preview_backpressure_count: int
    last_chunk_processed_at: str | None = None
    last_error_at: str | None = None
    last_error_message: str | None = None


class RuntimeMonitorLiveStreamResponse(BaseModel):
    """실시간 스트림 런타임 지표."""

    active_stream_count: int
    busy_stream_count: int
    idle_stream_count: int
    draining_stream_count: int
    pending_chunk_count: int
    max_pending_chunk_count: int
    coalesced_chunk_count: int
    max_running_streams: int
    pending_chunks_per_stream_limit: int
    worker_count: int
    busy_worker_count: int
    idle_worker_count: int


class RuntimeMonitorResponse(BaseModel):
    """런타임 운영 패널 응답."""

    generated_at: str
    active_session_count: int
    readiness: RuntimeMonitorReadinessResponse
    audio_pipeline: RuntimeMonitorAudioPipelineResponse
    live_stream: RuntimeMonitorLiveStreamResponse
