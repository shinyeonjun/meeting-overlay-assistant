import { createEmptyHistoryTimeline, createHistoryState } from "./history-defaults.js";

export function setHistoryRequestedScope(state, scope) {
    state.history.requestedScope = scope;
}

export function setHistoryLoading(state, loading) {
    state.history.loading = loading;
    if (loading) {
        state.history.errorMessage = "";
    }
}

export function setHistoryTimelineLoading(state, loading) {
    state.history.timelineLoading = loading;
}

export function setHistoryDetailLoading(state, loading) {
    state.history.detailLoading = loading;
}

export function setHistoryShareLoading(state, loading) {
    state.history.shareLoading = loading;
}

export function setHistoryShareStatus(state, message) {
    state.history.shareStatusText = message;
}

export function setHistoryError(state, message) {
    state.history.errorMessage = message;
    state.history.loading = false;
    state.history.detailLoading = false;
}

export function applyReportShares(state, items) {
    state.history.reportShares = items;
    state.history.shareLoading = false;
}

export function setHistoryReportContent(state, content) {
    state.history.selectedReportContent = content;
}

export function clearHistoryDetails(state) {
    state.history.reportShares = [];
    state.history.selectedReportContent = null;
    state.history.shareLoading = false;
    state.history.detailLoading = false;
    state.history.shareStatusText = "";
}

export function clearReportShares(state) {
    state.history.reportShares = [];
    state.history.shareLoading = false;
}

export function resetHistoryState(state) {
    const nextState = createHistoryState();
    state.history.sessions = nextState.sessions;
    state.history.reports = nextState.reports;
    state.history.sharedReports = nextState.sharedReports;
    state.history.timeline = createEmptyHistoryTimeline();
    state.history.reportShares = nextState.reportShares;
    state.history.effectiveScope = state.history.requestedScope;
    state.history.selectedKind = nextState.selectedKind;
    state.history.selectedId = nextState.selectedId;
    state.history.selectedReportContent = nextState.selectedReportContent;
    state.history.loading = nextState.loading;
    state.history.timelineLoading = nextState.timelineLoading;
    state.history.detailLoading = nextState.detailLoading;
    state.history.shareLoading = nextState.shareLoading;
    state.history.shareStatusText = nextState.shareStatusText;
    state.history.errorMessage = nextState.errorMessage;
    state.history.lastLoadedAt = nextState.lastLoadedAt;
}
