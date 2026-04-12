export function setSession(state, sessionPayload) {
    state.session.id = sessionPayload.id;
    state.session.source = sessionPayload.source;
    state.session.status = sessionPayload.status;
    state.session.startedAt = sessionPayload.startedAt ?? null;
    state.session.endedAt = sessionPayload.endedAt ?? null;
    state.session.primaryInputSource = sessionPayload.primaryInputSource ?? null;
    state.session.actualActiveSources = sessionPayload.actualActiveSources ?? [];
}

export function clearSessionTimer(state) {
    if (!state.session.overviewTimerId) {
        return;
    }

    window.clearInterval(state.session.overviewTimerId);
    state.session.overviewTimerId = null;
}

export function setSessionTimer(state, timerId) {
    state.session.overviewTimerId = timerId;
}

export function applyOverview(state, overviewPayload) {
    state.session.currentTopic = overviewPayload.currentTopic;
    state.session.overview.questions = overviewPayload.questions;
    state.session.overview.decisions = overviewPayload.decisions;
    state.session.overview.actionItems = overviewPayload.actionItems;
    state.session.overview.risks = overviewPayload.risks;
}
