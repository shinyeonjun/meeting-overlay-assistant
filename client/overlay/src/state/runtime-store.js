import { isClientSourceReady } from "../audio/source-policy.js";

export function applyRuntimeReadiness(state, payload, selectedSource) {
    state.runtime.serverReady = payload.backendReady === true;
    state.runtime.sttReady = payload.sttReady === true;
    state.runtime.warming = payload.warming !== false;
    state.runtime.preloadedSources = payload.preloadedSources ?? {};
    state.runtime.selectedSource = selectedSource;
    state.runtime.selectedSourceReady = isSourceReady(
        selectedSource,
        state.runtime.preloadedSources,
        state.runtime.bridgeReady,
    );
    state.runtime.startReady = (
        state.runtime.serverReady
        && state.runtime.sttReady
        && state.runtime.selectedSourceReady
    );
    state.runtime.lastCheckedAt = Date.now();
}

export function setBridgeReady(state, bridgeReady, selectedSource) {
    state.runtime.bridgeReady = bridgeReady === true;
    state.runtime.selectedSource = selectedSource;
    state.runtime.selectedSourceReady = isSourceReady(
        selectedSource,
        state.runtime.preloadedSources,
        state.runtime.bridgeReady,
    );
    state.runtime.startReady = (
        state.runtime.serverReady
        && state.runtime.sttReady
        && state.runtime.selectedSourceReady
    );
}

export function applyRuntimeMonitor(state, payload) {
    const monitor = payload?.audioPipeline ?? {};
    const liveStream = payload?.liveStream ?? {};
    state.runtime.monitor.activeSessionCount = payload?.activeSessionCount ?? 0;
    state.runtime.monitor.recentFinalCount = monitor.recentFinalCount ?? 0;
    state.runtime.monitor.recentUtteranceCount = monitor.recentUtteranceCount ?? 0;
    state.runtime.monitor.recentEventCount = monitor.recentEventCount ?? 0;
    state.runtime.monitor.averageQueueDelayMs = monitor.averageQueueDelayMs ?? null;
    state.runtime.monitor.maxQueueDelayMs = monitor.maxQueueDelayMs ?? null;
    state.runtime.monitor.lateFinalCount = monitor.lateFinalCount ?? 0;
    state.runtime.monitor.backpressureCount = monitor.backpressureCount ?? 0;
    state.runtime.monitor.filteredCount = monitor.filteredCount ?? 0;
    state.runtime.monitor.errorCount = monitor.errorCount ?? 0;
    state.runtime.monitor.lastChunkProcessedAt = monitor.lastChunkProcessedAt ?? null;
    state.runtime.monitor.lastErrorAt = monitor.lastErrorAt ?? null;
    state.runtime.monitor.lastErrorMessage = monitor.lastErrorMessage ?? "";
    state.runtime.monitor.liveStream.activeStreamCount = liveStream.activeStreamCount ?? 0;
    state.runtime.monitor.liveStream.busyStreamCount = liveStream.busyStreamCount ?? 0;
    state.runtime.monitor.liveStream.idleStreamCount = liveStream.idleStreamCount ?? 0;
    state.runtime.monitor.liveStream.drainingStreamCount = liveStream.drainingStreamCount ?? 0;
    state.runtime.monitor.liveStream.pendingChunkCount = liveStream.pendingChunkCount ?? 0;
    state.runtime.monitor.liveStream.maxPendingChunkCount = liveStream.maxPendingChunkCount ?? 0;
    state.runtime.monitor.liveStream.coalescedChunkCount = liveStream.coalescedChunkCount ?? 0;
    state.runtime.monitor.liveStream.maxRunningStreams = liveStream.maxRunningStreams ?? 0;
    state.runtime.monitor.liveStream.pendingChunksPerStreamLimit =
        liveStream.pendingChunksPerStreamLimit ?? 0;
    state.runtime.monitor.liveStream.workerCount = liveStream.workerCount ?? 0;
    state.runtime.monitor.liveStream.busyWorkerCount = liveStream.busyWorkerCount ?? 0;
    state.runtime.monitor.liveStream.idleWorkerCount = liveStream.idleWorkerCount ?? 0;
    state.runtime.monitor.updatedAt = payload?.generatedAt ?? null;
}

export function clearRuntimeMonitor(state) {
    state.runtime.monitor.activeSessionCount = 0;
    state.runtime.monitor.recentFinalCount = 0;
    state.runtime.monitor.recentUtteranceCount = 0;
    state.runtime.monitor.recentEventCount = 0;
    state.runtime.monitor.averageQueueDelayMs = null;
    state.runtime.monitor.maxQueueDelayMs = null;
    state.runtime.monitor.lateFinalCount = 0;
    state.runtime.monitor.backpressureCount = 0;
    state.runtime.monitor.filteredCount = 0;
    state.runtime.monitor.errorCount = 0;
    state.runtime.monitor.lastChunkProcessedAt = null;
    state.runtime.monitor.lastErrorAt = null;
    state.runtime.monitor.lastErrorMessage = "";
    state.runtime.monitor.liveStream.activeStreamCount = 0;
    state.runtime.monitor.liveStream.busyStreamCount = 0;
    state.runtime.monitor.liveStream.idleStreamCount = 0;
    state.runtime.monitor.liveStream.drainingStreamCount = 0;
    state.runtime.monitor.liveStream.pendingChunkCount = 0;
    state.runtime.monitor.liveStream.maxPendingChunkCount = 0;
    state.runtime.monitor.liveStream.coalescedChunkCount = 0;
    state.runtime.monitor.liveStream.maxRunningStreams = 0;
    state.runtime.monitor.liveStream.pendingChunksPerStreamLimit = 0;
    state.runtime.monitor.liveStream.workerCount = 0;
    state.runtime.monitor.liveStream.busyWorkerCount = 0;
    state.runtime.monitor.liveStream.idleWorkerCount = 0;
    state.runtime.monitor.updatedAt = null;
}

function isSourceReady(source, preloadedSources, bridgeReady) {
    return isClientSourceReady(source, preloadedSources, bridgeReady);
}
