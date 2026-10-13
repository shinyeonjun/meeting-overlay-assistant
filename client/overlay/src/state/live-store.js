import {
    createNormalizedOverviewEvent,
    resolveOverviewBucket,
} from "./session/overview-state.js";

const TERMINAL_ENDING_PATTERN =
    /(다|요|까|죠|네요|인가요|할까요|되나요|맞나요|합니다|했습니다|됩니다|예요|이에요|군요|습니다)[.!?…~]*$/u;
const CONTINUATION_ENDING_PATTERN =
    /(은|는|이|가|을|를|에|에서|와|과|도|만|으로|로|처럼|하고|해서|인데|이고|으며|면|때문에|관련해서|대해서|보면|같아서|같은데|근데|그리고|그래서|그러면)[.!?…~]*$/u;

export function setLiveSocket(state, socket) {
    state.live.socket = socket;
}

export function applyLiveUtterance(state, utterance, limit, now = Date.now()) {
    const previous = state.live.currentUtterance;
    const next = normalizeLiveUtterance(utterance, now);
    const completedLines = [];
    const completedMetrics = [];

    if (next.kind === "late_archive_final") {
        const line = commitHistoryEntry(state, next, limit);
        return {
            completedLines: line ? [line] : [],
            completedMetrics,
            activeLine: state.live.currentUtterance,
            shouldScheduleFinalize: false,
        };
    }

    if (previous && isDifferentSegment(previous, next)) {
        const line = finalizeCurrentUtterance(state, limit, "next_segment", now);
        if (line) {
            completedLines.push(line);
            completedMetrics.push(
                createFinalizeMetricsSnapshot(state.live.currentUtterance, "next_segment", now, 0),
            );
        }
    }

    const current = state.live.currentUtterance;
    const merged = mergeActiveUtterance(current, next, now);
    state.live.currentUtterance = merged;

    if (merged.phase === "final") {
        const line = finalizeCurrentUtterance(state, limit, "live_final", now);
        if (line) {
            completedLines.push(line);
            completedMetrics.push(
                createFinalizeMetricsSnapshot(state.live.currentUtterance, "live_final", now, 0),
            );
        }
        return {
            completedLines,
            completedMetrics,
            activeLine: state.live.currentUtterance,
            shouldScheduleFinalize: false,
        };
    }

    return {
        completedLines,
        completedMetrics,
        activeLine: state.live.currentUtterance,
        shouldScheduleFinalize: Boolean(state.live.currentUtterance?.text),
    };
}

export function clearCurrentUtterance(state) {
    clearActiveLineFinalizeTimer(state);
    state.live.currentUtterance = null;
}

export function finalizeCurrentUtterance(state, limit, reason, now = Date.now()) {
    const current = state.live.currentUtterance;
    if (!current?.text) {
        return null;
    }

    const wasCommitted = current.isCommitted === true;
    const finalized = {
        ...current,
        phase: "final",
        isCommitted: true,
        committedText: current.text,
        finalizeReason: reason ?? current.finalizeReason ?? "unknown",
        finalizedAt: current.finalizedAt ?? now,
        lastUpdatedAt: now,
    };

    state.live.currentUtterance = finalized;
    clearActiveLineFinalizeTimer(state);
    pushTranscriptHistory(state, finalized, limit);

    // 이미 내보낸 줄이라도 글자가 바뀌었으면(예: 쉼으로 먼저 닫힌 줄에 확정 자막이 온 경우) 다시 내보낸다.
    // 받는 쪽은 segmentId가 같은 줄을 새로 추가하지 않고 그 자리에서 고친다.
    if (wasCommitted && current.committedText === current.text) {
        return null;
    }

    return formatCompletedLine(finalized);
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
    const next = normalizeLiveUtterance(utterance);
    const nextSegmentId = next.segmentId ?? null;
    const deduped = state.live.transcriptHistory.filter((item) => {
        if (nextSegmentId && item.segmentId) {
            return item.segmentId !== nextSegmentId;
        }
        return item.id !== next.id;
    });
    state.live.transcriptHistory = [next, ...deduped].slice(0, limit);
}

export function hasSeenFeedEvent(state, eventId) {
    return state.live.seenFeedEventIds.has(eventId);
}

export function markFeedEventSeen(state, eventId) {
    state.live.seenFeedEventIds.add(eventId);
}

export function clearActiveLineFinalizeTimer(state) {
    if (state.live.activeLineFinalizeTimerId !== null) {
        window.clearTimeout(state.live.activeLineFinalizeTimerId);
        state.live.activeLineFinalizeTimerId = null;
    }
}

export function setActiveLineFinalizeTimer(state, timerId) {
    clearActiveLineFinalizeTimer(state);
    state.live.activeLineFinalizeTimerId = timerId;
}

export function resolveActiveLineFinalizeDelayMs(utterance, baseTimeoutMs, softDelayMs) {
    if (!utterance?.text) {
        return baseTimeoutMs;
    }
    return shouldApplySoftDelay(utterance.text)
        ? baseTimeoutMs + softDelayMs
        : baseTimeoutMs;
}

export function createFinalizeMetricsSnapshot(
    utterance,
    reason,
    now = Date.now(),
    delayMs = 0,
) {
    if (!utterance?.text) {
        return null;
    }

    const latencyMs = Math.max(0, now - (utterance.firstSeenAt ?? now));
    const softDelayed = delayMs > 0 && shouldApplySoftDelay(utterance.text);
    return {
        segmentId: utterance.segmentId ?? null,
        finalizeReason: reason ?? utterance.finalizeReason ?? "unknown",
        mutationCount: utterance.mutationCount ?? 0,
        latencyMs,
        textLength: utterance.text.length,
        softDelayed,
        likelyFragmented: softDelayed && reason !== "live_final",
        finalizedAt: now,
    };
}

export function recordFinalizeMetrics(state, metrics, limit = 40) {
    if (!metrics) {
        return;
    }

    state.live.metrics.recentFinalizeEvents = [
        metrics,
        ...(state.live.metrics.recentFinalizeEvents ?? []),
    ].slice(0, limit);
}

function commitHistoryEntry(state, utterance, limit) {
    pushTranscriptHistory(
        state,
        {
            ...utterance,
            phase: "final",
            isCommitted: true,
            finalizeReason: utterance.finalizeReason ?? "late_archive_final",
            finalizedAt: utterance.finalizedAt ?? utterance.lastUpdatedAt ?? Date.now(),
        },
        limit,
    );
    return formatCompletedLine(utterance);
}

function mergeActiveUtterance(previous, next, now) {
    if (!previous || isDifferentSegment(previous, next)) {
        return {
            ...next,
            phase: next.phase,
            firstSeenAt: now,
            lastUpdatedAt: now,
            mutationCount: next.text ? 1 : 0,
            isCommitted: false,
            finalizeReason: null,
            finalizedAt: null,
        };
    }

    const textChanged = previous.text !== next.text;
    const keepCommitted = previous.isCommitted === true && next.phase === "final";
    // 쉼 타이머로 먼저 닫힌 줄에 같은 구간의 회색 자막이 다시 오면 줄을 다시 연다.
    // 단계를 final에 묶어 두면 회색 자막이 올 때마다 다시 확정 처리돼 목록에 같은 문장이 쌓인다.
    const reopened = previous.isCommitted === true && next.phase !== "final";
    return {
        ...previous,
        ...next,
        phase: reopened ? next.phase : upgradePhase(previous.phase, next.phase),
        firstSeenAt: previous.firstSeenAt ?? now,
        lastUpdatedAt: now,
        mutationCount: textChanged
            ? (previous.mutationCount ?? 0) + 1
            : (previous.mutationCount ?? 0),
        isCommitted: keepCommitted,
        committedText: previous.committedText ?? null,
        finalizeReason: keepCommitted ? previous.finalizeReason : null,
        finalizedAt: keepCommitted ? previous.finalizedAt : null,
    };
}

function normalizeLiveUtterance(utterance, now = Date.now()) {
    // 서버 payload(snake_case)와 이미 정리된 줄(camelCase)을 모두 받는다.
    // 정리된 줄을 다시 넣을 때 segmentId를 잃으면 기록이 구간별로 합쳐지지 않는다.
    const kind = normalizeUtteranceKind(utterance.kind);
    const isPartial = (utterance.is_partial ?? utterance.isPartial) === true;
    return {
        id: utterance.id,
        seqNum: utterance.seq_num ?? utterance.seqNum,
        segmentId: utterance.segment_id ?? utterance.segmentId ?? null,
        text: utterance.text ?? "",
        confidence: utterance.confidence ?? 0,
        startMs: utterance.start_ms ?? utterance.startMs ?? null,
        endMs: utterance.end_ms ?? utterance.endMs ?? null,
        speakerLabel: utterance.speaker_label ?? utterance.speakerLabel ?? "",
        isPartial,
        inputSource: utterance.input_source ?? utterance.inputSource ?? null,
        kind,
        stability: utterance.stability ?? null,
        phase: utterance.phase ?? resolvePhase(kind, utterance.stability, isPartial),
        firstSeenAt: utterance.firstSeenAt ?? now,
        lastUpdatedAt: utterance.lastUpdatedAt ?? now,
        mutationCount: utterance.mutationCount ?? 0,
        isCommitted: utterance.isCommitted === true,
        committedText: utterance.committedText ?? null,
        finalizeReason: utterance.finalizeReason ?? null,
        finalizedAt: utterance.finalizedAt ?? null,
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

function resolvePhase(kind, stability, isPartial) {
    if (stability === "low" || (isPartial && kind === "preview")) {
        return "draft";
    }
    if (stability === "medium" || kind === "live_final") {
        return "settling";
    }
    return "final";
}

function upgradePhase(previousPhase, nextPhase) {
    const priority = {
        draft: 0,
        settling: 1,
        final: 2,
    };
    return priority[nextPhase] >= priority[previousPhase] ? nextPhase : previousPhase;
}

function isDifferentSegment(previous, next) {
    return Boolean(previous?.segmentId) && Boolean(next?.segmentId) && previous.segmentId !== next.segmentId;
}

function formatCompletedLine(utterance) {
    if (!utterance?.text) {
        return null;
    }
    const text = utterance.speakerLabel
        ? `${utterance.speakerLabel}: ${utterance.text}`
        : utterance.text;
    return { text, segmentId: utterance.segmentId ?? null };
}

function shouldApplySoftDelay(text) {
    const normalized = text?.trim();
    if (!normalized) {
        return false;
    }
    if (TERMINAL_ENDING_PATTERN.test(normalized)) {
        return false;
    }
    return CONTINUATION_ENDING_PATTERN.test(normalized);
}
