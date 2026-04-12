export function createEmptyCarryOver() {
    return {
        decisions: [],
        actionItems: [],
        risks: [],
        questions: [],
    };
}

export function createEmptyRetrievalBrief() {
    return {
        query: null,
        resultCount: 0,
        items: [],
    };
}

export function createEmptyHistoryTimeline() {
    return {
        sessionCount: 0,
        reportCount: 0,
        sessions: [],
        reports: [],
        carryOver: createEmptyCarryOver(),
        retrievalBrief: createEmptyRetrievalBrief(),
        lastLoadedAt: null,
    };
}

export function createHistoryState() {
    return {
        sessions: [],
        reports: [],
        sharedReports: [],
        timeline: createEmptyHistoryTimeline(),
        reportShares: [],
        requestedScope: "mine",
        effectiveScope: "mine",
        selectedKind: null,
        selectedId: null,
        selectedReportContent: null,
        loading: false,
        timelineLoading: false,
        detailLoading: false,
        shareLoading: false,
        shareStatusText: "",
        errorMessage: "",
        lastLoadedAt: null,
    };
}
