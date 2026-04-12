"""런타임 모니터링 API 스키마."""

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
