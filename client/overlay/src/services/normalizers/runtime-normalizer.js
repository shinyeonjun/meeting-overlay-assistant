/** 오버레이에서 공통 관련 runtime normalizer 서비스를 제공한다. */
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
            liveFinalCompareCount: monitor.live_final_compare_count ?? 0,
            liveFinalExactMatchCount: monitor.live_final_exact_match_count ?? 0,
            liveFinalChangedCount: monitor.live_final_changed_count ?? 0,
            liveFinalChangeRatio: monitor.live_final_change_ratio ?? 0,
            liveFinalAverageSimilarity: monitor.live_final_average_similarity ?? null,
            liveFinalAverageDelayMs: monitor.live_final_average_delay_ms ?? null,
            previewCandidateCount: monitor.preview_candidate_count ?? 0,
            previewCandidatePreviewCount: monitor.preview_candidate_preview_count ?? 0,
            previewCandidateLiveFinalCount: monitor.preview_candidate_live_final_count ?? 0,
            previewFirstAttemptedAnchorAtMs:
                monitor.preview_first_attempted_anchor_at_ms ?? null,
            previewTimelineAnchorAtMs: monitor.preview_timeline_anchor_at_ms ?? null,
            previewFirstProductiveGapMs:
                monitor.preview_first_productive_gap_ms ?? null,
            previewEmptyCyclesBeforeFirstCandidateCount:
                monitor.preview_empty_cycles_before_first_candidate_count ?? 0,
            previewFirstReadyAtMs: monitor.preview_first_ready_at_ms ?? null,
            previewFirstJobStartedAtMs: monitor.preview_first_job_started_at_ms ?? null,
            previewFirstPickedAtMs: monitor.preview_first_picked_at_ms ?? null,
            previewFirstSherpaNonEmptyAtMs: monitor.preview_first_sherpa_non_empty_at_ms ?? null,
            previewFirstCandidateAtMs: monitor.preview_first_candidate_at_ms ?? null,
            previewFirstReadyRelativeMs:
                monitor.preview_first_ready_relative_ms ?? null,
            previewFirstJobStartedRelativeMs:
                monitor.preview_first_job_started_relative_ms ?? null,
            previewFirstPickedRelativeMs:
                monitor.preview_first_picked_relative_ms ?? null,
            previewFirstSherpaNonEmptyRelativeMs:
                monitor.preview_first_sherpa_non_empty_relative_ms ?? null,
            previewFirstCandidateRelativeMs:
                monitor.preview_first_candidate_relative_ms ?? null,
            previewFirstReadyPendingFinalChunkCount:
                monitor.preview_first_ready_pending_final_chunk_count ?? null,
            previewFirstReadyBusyWorkerCount:
                monitor.preview_first_ready_busy_worker_count ?? null,
            previewFirstPickedPendingFinalChunkCount:
                monitor.preview_first_picked_pending_final_chunk_count ?? null,
            previewFirstPickedBusyWorkerCount:
                monitor.preview_first_picked_busy_worker_count ?? null,
            previewNotifySkippedBusyCount:
                monitor.preview_notify_skipped_busy_count ?? 0,
            previewNotifySkippedPreferredFinalCount:
                monitor.preview_notify_skipped_preferred_final_count ?? 0,
            previewFirstBusySkipAtMs:
                monitor.preview_first_busy_skip_at_ms ?? null,
            previewFirstPreferredFinalSkipAtMs:
                monitor.preview_first_preferred_final_skip_at_ms ?? null,
            previewFirstBusySkipRelativeMs:
                monitor.preview_first_busy_skip_relative_ms ?? null,
            previewFirstPreferredFinalSkipRelativeMs:
                monitor.preview_first_preferred_final_skip_relative_ms ?? null,
            previewFirstBusySkipPendingFinalChunkCount:
                monitor.preview_first_busy_skip_pending_final_chunk_count ?? null,
            previewFirstBusySkipHasPendingPreviewChunk:
                monitor.preview_first_busy_skip_has_pending_preview_chunk ?? null,
            previewFirstBusySkipBusyWorkerCount:
                monitor.preview_first_busy_skip_busy_worker_count ?? null,
            previewFirstBusySkipBusyJobKind:
                monitor.preview_first_busy_skip_busy_job_kind ?? null,
            previewFirstPreferredFinalSkipPendingFinalChunkCount:
                monitor.preview_first_preferred_final_skip_pending_final_chunk_count ?? null,
            previewFirstPreferredFinalSkipHasPendingPreviewChunk:
                monitor.preview_first_preferred_final_skip_has_pending_preview_chunk ?? null,
            previewFirstPreferredFinalSkipBusyWorkerCount:
                monitor.preview_first_preferred_final_skip_busy_worker_count ?? null,
            previewFirstPreferredFinalSkipBusyJobKind:
                monitor.preview_first_preferred_final_skip_busy_job_kind ?? null,
            previewEmittedCount: monitor.preview_emitted_count ?? 0,
            previewEmittedPreviewCount: monitor.preview_emitted_preview_count ?? 0,
            previewEmittedLiveFinalCount: monitor.preview_emitted_live_final_count ?? 0,
            previewGuardRejectedCount: monitor.preview_guard_rejected_count ?? 0,
            previewLengthRejectedCount: monitor.preview_length_rejected_count ?? 0,
            previewBackpressureCount: monitor.preview_backpressure_count ?? 0,
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
