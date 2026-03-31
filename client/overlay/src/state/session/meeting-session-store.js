import { createEmptyOverviewBuckets } from "./overview-state.js";

export function setSession(state, sessionPayload) {
    const nextSessionId = sessionPayload.id ?? null;
    const previousSessionId = state.session.id;
    const nextStatus = sessionPayload.status ?? state.session.status;

    if (
        previousSessionId !== nextSessionId
        || nextStatus === "draft"
        || nextStatus === "ended"
        || nextStatus === "archived"
        || nextStatus === "idle"
    ) {
        state.session.liveOverview = createEmptyOverviewBuckets();
    }

    state.session.id = sessionPayload.id;
    state.session.title = sessionPayload.title ?? null;
    state.session.status = sessionPayload.status;
    state.session.startedAt = sessionPayload.startedAt ?? null;
    state.session.endedAt = sessionPayload.endedAt ?? null;
    state.session.accountId = sessionPayload.accountId ?? null;
    state.session.contactId = sessionPayload.contactId ?? null;
    state.session.contextThreadId = sessionPayload.contextThreadId ?? null;
    state.session.participants = sessionPayload.participants ?? [];
    state.session.participantLinks = sessionPayload.participantLinks ?? [];
    state.session.participantCandidates = sessionPayload.participantCandidates ?? [];
    state.session.participantFollowups = sessionPayload.participantFollowups ?? [];
    state.session.participationSummary = sessionPayload.participationSummary ?? {
        totalCount: 0,
        linkedCount: 0,
        unmatchedCount: 0,
        ambiguousCount: 0,
        unresolvedCount: 0,
        pendingFollowupCount: 0,
        resolvedFollowupCount: 0,
    };
    state.session.primaryInputSource = sessionPayload.primaryInputSource ?? null;
    state.session.actualActiveSources = sessionPayload.actualActiveSources ?? [];
}

export function setSessionParticipation(state, participationPayload) {
    state.session.participantLinks = participationPayload.participants ?? [];
    state.session.participantCandidates = participationPayload.participantCandidates ?? [];
    state.session.participationSummary = participationPayload.summary ?? {
        totalCount: 0,
        linkedCount: 0,
        unmatchedCount: 0,
        ambiguousCount: 0,
        unresolvedCount: 0,
        pendingFollowupCount: 0,
        resolvedFollowupCount: 0,
    };
}

export function setSessionParticipantFollowups(state, followups) {
    state.session.participantFollowups = followups ?? [];
}

export function setSessionParticipants(state, participantsText) {
    state.session.participantsText = participantsText ?? "";
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
