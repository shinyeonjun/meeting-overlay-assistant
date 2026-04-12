import { createHistoryState } from "./history/history-defaults.js";

function createSessionState() {
    return {
        id: null,
        title: null,
        status: "idle",
        startedAt: null,
        endedAt: null,
        accountId: null,
        contactId: null,
        contextThreadId: null,
        participants: [],
        participantLinks: [],
        participantCandidates: [],
        participantFollowups: [],
        participationSummary: {
            totalCount: 0,
            linkedCount: 0,
            unmatchedCount: 0,
            ambiguousCount: 0,
            unresolvedCount: 0,
            pendingFollowupCount: 0,
            resolvedFollowupCount: 0,
        },
        participantsText: "",
        primaryInputSource: null,
        actualActiveSources: [],
        overviewTimerId: null,
        currentTopic: null,
        overview: {
            questions: [],
            decisions: [],
            actionItems: [],
            risks: [],
        },
    };
}

function createLiveState() {
    return {
        socket: null,
        connectionStatus: "idle",
        currentUtterance: null,
        transcriptHistory: [],
        seenFeedEventIds: new Set(),
    };
}

function createEventsState() {
    return {
        items: [],
        editingEventId: null,
        grouped: {
            questions: [],
            decisions: [],
            actionItems: [],
            risks: [],
        },
        lastLoadedAt: null,
    };
}

function createReportState() {
    return {
        latestReportId: null,
        latestReportType: null,
        latestVersion: null,
        generatedAt: null,
        latestPath: null,
        status: "idle",
    };
}

function createRuntimeState() {
    return {
        bridgeReady: false,
        serverReady: false,
        sttReady: false,
        warming: true,
        startReady: false,
        selectedSourceReady: false,
        selectedSource: null,
        preloadedSources: {},
        lastCheckedAt: null,
        monitor: {
            activeSessionCount: 0,
            recentFinalCount: 0,
            recentUtteranceCount: 0,
            recentEventCount: 0,
            averageQueueDelayMs: null,
            maxQueueDelayMs: null,
            lateFinalCount: 0,
            backpressureCount: 0,
            filteredCount: 0,
            errorCount: 0,
            lastChunkProcessedAt: null,
            lastErrorAt: null,
            lastErrorMessage: "",
            liveStream: {
                activeStreamCount: 0,
                busyStreamCount: 0,
                idleStreamCount: 0,
                drainingStreamCount: 0,
                pendingChunkCount: 0,
                maxPendingChunkCount: 0,
                coalescedChunkCount: 0,
                maxRunningStreams: 0,
                pendingChunksPerStreamLimit: 0,
                workerCount: 0,
                busyWorkerCount: 0,
                idleWorkerCount: 0,
            },
            updatedAt: null,
        },
    };
}

function createAuthState() {
    return {
        initialized: false,
        authEnabled: false,
        bootstrapRequired: false,
        userCount: 0,
        serverUrl: null,
        accessToken: null,
        user: null,
        autoLoginEnabled: true,
    };
}

function createContextState() {
    return {
        accounts: [],
        contacts: [],
        threads: [],
        selectedAccountId: "",
        selectedContactId: "",
        selectedThreadId: "",
        loading: false,
        errorMessage: "",
        lastLoadedAt: null,
    };
}

export const appState = {
    session: createSessionState(),
    live: createLiveState(),
    events: createEventsState(),
    report: createReportState(),
    runtime: createRuntimeState(),
    auth: createAuthState(),
    history: createHistoryState(),
    context: createContextState(),
};
