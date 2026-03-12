export function setLiveSocket(state, socket) {
    state.live.socket = socket;
}

export function applyLiveUtterance(state, utterance, limit) {
    const previous = state.live.currentUtterance;
    const next = normalizeLiveUtterance(utterance);
    const isNewSegment = previous && previous.segmentId !== next.segmentId;
    const shouldKeepPreviousVisible =
        isNewSegment
        && isLowStabilityPartial(next)
        && hasStableVisibleUtterance(previous);

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

    if (!shouldKeepPreviousVisible) {
        state.live.currentUtterance = next;
    }

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
        const target = resolveOverviewBucket(state, event.type);
        if (!target) {
            continue;
        }

        const existingIndex = target.findIndex((item) => item.id === event.id);
        const normalizedEvent = {
            id: event.id,
            title: event.title,
            state: event.state,
            speaker_label: event.speaker_label,
        };

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
        kind: utterance.kind ?? "final",
        stability: utterance.stability ?? null,
    };
}

function isLowStabilityPartial(utterance) {
    return utterance.isPartial && (utterance.stability === "low" || utterance.kind === "partial");
}

function hasStableVisibleUtterance(utterance) {
    return Boolean(
        utterance
        && utterance.text
        && (!utterance.isPartial || utterance.stability === "medium" || utterance.kind === "fast_final")
    );
}

function resolveOverviewBucket(state, eventType) {
    if (eventType === "question") {
        return state.session.overview.questions;
    }
    if (eventType === "decision") {
        return state.session.overview.decisions;
    }
    if (eventType === "action_item") {
        return state.session.overview.actionItems;
    }
    if (eventType === "risk") {
        return state.session.overview.risks;
    }
    return null;
}
