import {
    createNormalizedOverviewEvent,
    resolveOverviewBucket,
} from "./session/overview-state.js";

export function setLiveSocket(state, socket) {
    state.live.socket = socket;
}

export function applyLiveUtterance(state, utterance, limit) {
    const previous = state.live.currentUtterance;
    const next = normalizeLiveUtterance(utterance);
    const isLateArchiveFinal = next.kind === "late_archive_final";
    const isNewSegment = previous && previous.segmentId !== next.segmentId;

    let completedLine = null;
    if (
        previous
        && isNewSegment
        && previous.text
        && !previous.isPartial
    ) {
        completedLine = previous.speakerLabel
            ? `${previous.speakerLabel}: ${previous.text}`
            : previous.text;
    }

    if (isLateArchiveFinal) {
        pushTranscriptHistory(state, utterance, limit);
        return next.speakerLabel
            ? `${next.speakerLabel}: ${next.text}`
            : next.text;
    }

    state.live.currentUtterance = next;

    if (!next.isPartial) {
        pushTranscriptHistory(state, utterance, limit);
    }

    return completedLine;
}

export function clearCurrentUtterance(state) {
    state.live.currentUtterance = null;
}

export function applyLiveEvents(state, events) {
    for (const event of events) {
        const target = resolveOverviewBucket(state.session.liveOverview, event.type);
        if (!target) {
            continue;
        }

        const existingIndex = target.findIndex((item) => item.id === event.id);
        const normalizedEvent = createNormalizedOverviewEvent(event);

        if (existingIndex >= 0) {
            target[existingIndex] = normalizedEvent;
            continue;
        }

        target.unshift(normalizedEvent);
    }
}

export function setLiveConnectionStatus(state, status) {
    state.live.connectionStatus = status;
}

export function pushTranscriptHistory(state, utterance, limit) {
    state.live.transcriptHistory = [utterance, ...state.live.transcriptHistory].slice(0, limit);
}

export function hasSeenFeedEvent(state, eventId) {
    return state.live.seenFeedEventIds.has(eventId);
}

export function markFeedEventSeen(state, eventId) {
    state.live.seenFeedEventIds.add(eventId);
}

function normalizeLiveUtterance(utterance) {
    return {
        id: utterance.id,
        seqNum: utterance.seq_num,
        segmentId: utterance.segment_id ?? null,
        text: utterance.text ?? "",
        confidence: utterance.confidence ?? 0,
        startMs: utterance.start_ms ?? null,
        endMs: utterance.end_ms ?? null,
        speakerLabel: utterance.speaker_label ?? "",
        isPartial: utterance.is_partial === true,
        inputSource: utterance.input_source ?? null,
        kind: normalizeUtteranceKind(utterance.kind),
        stability: utterance.stability ?? null,
    };
}

function normalizeUtteranceKind(kind) {
    if (kind === "partial") {
        return "preview";
    }
    if (kind === "fast_final") {
        return "live_final";
    }
    if (kind === "final") {
        return "archive_final";
    }
    if (kind === "late_final") {
        return "late_archive_final";
    }
    return kind ?? "archive_final";
}
