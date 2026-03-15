export function normalizeRuntimeReadinessPayload(payload) {
    return {
        backendReady: payload.backend_ready === true,
        warming: payload.warming !== false,
        sttReady: payload.stt_ready === true,
        sttPreloadEnabled: payload.stt_preload_enabled !== false,
        preloadedSources: payload.preloaded_sources ?? {},
    };
}

export function normalizeRuntimeMonitorPayload(payload) {
    const monitor = payload?.audio_pipeline ?? {};
    const liveStream = payload?.live_stream ?? {};
    return {
        generatedAt: payload?.generated_at ?? null,
        activeSessionCount: payload?.active_session_count ?? 0,
        readiness: payload?.readiness
            ? normalizeRuntimeReadinessPayload(payload.readiness)
            : null,
        audioPipeline: {
            recentFinalCount: monitor.recent_final_count ?? 0,
            recentUtteranceCount: monitor.recent_utterance_count ?? 0,
            recentEventCount: monitor.recent_event_count ?? 0,
            averageQueueDelayMs: monitor.average_queue_delay_ms ?? null,
            maxQueueDelayMs: monitor.max_queue_delay_ms ?? null,
            lateFinalCount: monitor.late_final_count ?? 0,
            backpressureCount: monitor.backpressure_count ?? 0,
            filteredCount: monitor.filtered_count ?? 0,
            errorCount: monitor.error_count ?? 0,
            matchedCount: monitor.matched_count ?? 0,
            graceMatchedCount: monitor.grace_matched_count ?? 0,
            standaloneCount: monitor.standalone_count ?? 0,
            standaloneRatio: monitor.standalone_ratio ?? 0,
            lastChunkProcessedAt: monitor.last_chunk_processed_at ?? null,
            lastErrorAt: monitor.last_error_at ?? null,
            lastErrorMessage: monitor.last_error_message ?? "",
        },
        liveStream: {
            activeStreamCount: liveStream.active_stream_count ?? 0,
            busyStreamCount: liveStream.busy_stream_count ?? 0,
            idleStreamCount: liveStream.idle_stream_count ?? 0,
            drainingStreamCount: liveStream.draining_stream_count ?? 0,
            pendingChunkCount: liveStream.pending_chunk_count ?? 0,
            maxPendingChunkCount: liveStream.max_pending_chunk_count ?? 0,
            coalescedChunkCount: liveStream.coalesced_chunk_count ?? 0,
            maxRunningStreams: liveStream.max_running_streams ?? 0,
            pendingChunksPerStreamLimit: liveStream.pending_chunks_per_stream_limit ?? 0,
            workerCount: liveStream.worker_count ?? 0,
            busyWorkerCount: liveStream.busy_worker_count ?? 0,
            idleWorkerCount: liveStream.idle_worker_count ?? 0,
        },
    };
}
