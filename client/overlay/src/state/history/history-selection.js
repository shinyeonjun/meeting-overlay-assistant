import { createEmptyHistoryTimeline } from "./history-defaults.js";

function ensureSelectedItem(state) {
    const hasSelectedSession = state.history.sessions.some(
        (item) => item.id === state.history.selectedId,
    );
    const hasSelectedReport = state.history.reports.some(
        (item) => item.id === state.history.selectedId,
    );
    const hasSelectedSharedReport = state.history.sharedReports.some(
        (item) => item.reportId === state.history.selectedId,
    );

    if (
        (state.history.selectedKind === "session" && hasSelectedSession)
        || (state.history.selectedKind === "report" && hasSelectedReport)
        || (state.history.selectedKind === "shared-report" && hasSelectedSharedReport)
    ) {
        return;
    }

    if (state.history.sessions.length > 0) {
        state.history.selectedKind = "session";
        state.history.selectedId = state.history.sessions[0].id;
        return;
    }

    if (state.history.reports.length > 0) {
        state.history.selectedKind = "report";
        state.history.selectedId = state.history.reports[0].id;
        return;
    }

    if (state.history.sharedReports.length > 0) {
        state.history.selectedKind = "shared-report";
        state.history.selectedId = state.history.sharedReports[0].reportId;
        return;
    }

    state.history.selectedKind = null;
    state.history.selectedId = null;
}

export function applyHistorySnapshot(
    state,
    { sessions, reports, sharedReports, effectiveScope },
) {
    state.history.sessions = sessions;
    state.history.reports = reports;
    state.history.sharedReports = sharedReports;
    state.history.effectiveScope = effectiveScope;
    state.history.loading = false;
    state.history.errorMessage = "";
    state.history.lastLoadedAt = Date.now();
    ensureSelectedItem(state);
}

export function applyHistoryTimeline(state, payload) {
    const emptyTimeline = createEmptyHistoryTimeline();
    state.history.timeline = {
        sessionCount: payload.sessionCount ?? 0,
        reportCount: payload.reportCount ?? 0,
        sessions: payload.sessions ?? [],
        reports: payload.reports ?? [],
        carryOver: payload.carryOver ?? emptyTimeline.carryOver,
        retrievalBrief: payload.retrievalBrief ?? emptyTimeline.retrievalBrief,
        lastLoadedAt: Date.now(),
    };
    state.history.timelineLoading = false;
}

export function clearHistoryTimeline(state) {
    state.history.timeline = createEmptyHistoryTimeline();
    state.history.timelineLoading = false;
}

export function selectHistoryItem(state, kind, id) {
    state.history.selectedKind = kind;
    state.history.selectedId = id;
}

export function findSelectedHistoryItem(state) {
    if (state.history.selectedKind === "session") {
        return state.history.sessions.find(
            (item) => item.id === state.history.selectedId,
        ) ?? null;
    }
    if (state.history.selectedKind === "report") {
        return state.history.reports.find(
            (item) => item.id === state.history.selectedId,
        ) ?? null;
    }
    if (state.history.selectedKind === "shared-report") {
        return state.history.sharedReports.find(
            (item) => item.reportId === state.history.selectedId,
        ) ?? null;
    }
    return null;
}
