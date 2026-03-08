function createSessionState() {
    return {
        id: null,
        source: null,
        status: "idle",
        startedAt: null,
        endedAt: null,
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
        selectedIds: new Set(),
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
        content: "",
        speakerTranscript: [],
        speakerEvents: [],
        history: [],
        status: "idle",
    };
}

function createRuntimeState() {
    return {
        bridgeReady: false,
        backendReady: false,
        sttReady: false,
        warming: true,
        startReady: false,
        selectedSourceReady: false,
        selectedSource: null,
        preloadedSources: {},
        lastCheckedAt: null,
    };
}

export const appState = {
    session: createSessionState(),
    live: createLiveState(),
    events: createEventsState(),
    report: createReportState(),
    runtime: createRuntimeState(),
};
