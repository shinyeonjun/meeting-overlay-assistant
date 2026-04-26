import {
    ACTIVE_LINE_FINALIZE_TIMEOUT_MS,
    ACTIVE_LINE_SOFT_DELAY_MS,
    LIVE_EVENT_INSIGHTS_ENABLED,
    TRANSCRIPT_HISTORY_LIMIT,
} from "../../config/constants.js";
import { normalizeStreamPayload } from "../../services/payload-normalizers.js";
import { appState } from "../../state/app-state.js";
import {
    applyLiveEvents,
    applyLiveUtterance,
    clearCurrentUtterance,
    createFinalizeMetricsSnapshot,
    finalizeCurrentUtterance,
    recordFinalizeMetrics,
    removeTranscriptHistoryEntry,
    resolveActiveLineFinalizeDelayMs,
    setActiveLineFinalizeTimer,
} from "../../state/live-store.js";
import { mergeOverviewBuckets } from "../../state/session/overview-state.js";
import { renderEventBoard } from "../events-board-controller.js";
import { pushCompletedCaptionLine, renderCurrentUtterance } from "./live-caption-renderer.js";
import { shouldSuppressSilenceFinalizeCommit } from "./live-caption-policy.js";
import { pushEventFeed } from "./live-feed.js";

function scheduleActiveLineFinalize() {
    const current = appState.live.currentUtterance;
    if (!current?.text || current.phase === "final") {
        setActiveLineFinalizeTimer(appState, null);
        return;
    }

    const finalizeDelayMs = resolveActiveLineFinalizeDelayMs(
        current,
        ACTIVE_LINE_FINALIZE_TIMEOUT_MS,
        ACTIVE_LINE_SOFT_DELAY_MS,
    );
    const timerId = window.setTimeout(() => {
        appState.live.activeLineFinalizeTimerId = null;
        const completedLine = finalizeCurrentUtterance(
            appState,
            TRANSCRIPT_HISTORY_LIMIT,
            "silence",
        );
        const metrics = createFinalizeMetricsSnapshot(
            appState.live.currentUtterance,
            "silence",
            Date.now(),
            finalizeDelayMs,
        );
        recordFinalizeMetrics(appState, metrics);
        emitFinalizeMetrics(metrics);
        if (shouldSuppressSilenceFinalizeCommit(completedLine, metrics)) {
            removeTranscriptHistoryEntry(
                appState,
                appState.live.currentUtterance?.id ?? null,
            );
            clearCurrentUtterance(appState);
        } else {
            pushCompletedCaptionLine(completedLine, {
                finalizeReason: metrics?.finalizeReason ?? "silence",
            });
        }
        renderCurrentUtterance();
    }, finalizeDelayMs);

    setActiveLineFinalizeTimer(appState, timerId);
}

export function handlePipelinePayload(event) {
    let payload;
    try {
        let raw = JSON.parse(event.data);

        if (raw.type === "payload" && raw.payload) {
            raw = raw.payload;
        } else if (raw.type === "session") {
            return;
        }

        payload = normalizeStreamPayload(raw);
    } catch (error) {
        console.warn("[CAPS] payload parse failed:", error, event.data);
        return;
    }

    if (!payload.utterances.length && (!LIVE_EVENT_INSIGHTS_ENABLED || !payload.events.length)) {
        return;
    }

    for (const utterance of payload.utterances) {
        try {
            const result = applyLiveUtterance(
                appState,
                utterance,
                TRANSCRIPT_HISTORY_LIMIT,
            );
            for (let index = 0; index < (result.completedLines ?? []).length; index += 1) {
                const completedLine = result.completedLines[index];
                const metrics = result.completedMetrics?.[index] ?? null;
                pushCompletedCaptionLine(completedLine, {
                    finalizeReason: metrics?.finalizeReason ?? "live_final",
                });
            }
            for (const metrics of result.completedMetrics ?? []) {
                recordFinalizeMetrics(appState, metrics);
                emitFinalizeMetrics(metrics);
            }
            if (result.shouldScheduleFinalize) {
                scheduleActiveLineFinalize();
            } else {
                setActiveLineFinalizeTimer(appState, null);
            }
            renderCurrentUtterance();
        } catch (error) {
            console.warn("[CAPS] live utterance processing failed:", error, utterance);
        }
    }

    if (LIVE_EVENT_INSIGHTS_ENABLED) {
        try {
            applyLiveEvents(appState, payload.events);
            const mergedOverview = mergeOverviewBuckets(
                appState.session.overview,
                appState.session.liveOverview,
            );
            renderEventBoard();
            pushEventFeed("question", mergedOverview.questions);
        } catch (error) {
            console.warn("[CAPS] live event processing failed:", error, payload.events);
        }
    }
}

function emitFinalizeMetrics(metrics) {
    if (!metrics) {
        return;
    }
    console.debug("[CAPS][live-metrics] finalize", metrics);
}
