/** 오버레이에서 실시간 흐름의 live payload handler 제어를 담당한다. */
import {
    ACTIVE_LINE_FINALIZE_TIMEOUT_MS,
    ACTIVE_LINE_SOFT_DELAY_MS,
    TRANSCRIPT_HISTORY_LIMIT,
} from "../../config/constants.js";
import { normalizeStreamPayload } from "../../services/payload-normalizers.js";
import { appState } from "../../state/app-state.js";
import {
    applyLiveEvents,
    applyLiveUtterance,
    createFinalizeMetricsSnapshot,
    finalizeCurrentUtterance,
    recordFinalizeMetrics,
    resolveActiveLineFinalizeDelayMs,
    setActiveLineFinalizeTimer,
} from "../../state/live-store.js";
import { mergeOverviewBuckets } from "../../state/session/overview-state.js";
import { renderEventBoard } from "../events-board-controller.js";
import { pushCompletedCaptionLine, renderCurrentUtterance } from "./live-caption-renderer.js";
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
        pushCompletedCaptionLine(completedLine);
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

    if (!payload.utterances.length && !payload.events.length) {
        return;
    }

    for (const utterance of payload.utterances) {
        try {
            const result = applyLiveUtterance(
                appState,
                utterance,
                TRANSCRIPT_HISTORY_LIMIT,
            );
            for (const completedLine of result.completedLines ?? []) {
                pushCompletedCaptionLine(completedLine);
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

    try {
        applyLiveEvents(appState, payload.events);
        const mergedOverview = mergeOverviewBuckets(
            appState.session.overview,
            appState.session.liveOverview,
        );
        renderEventBoard();
        pushEventFeed("question", mergedOverview.questions);
        pushEventFeed("decision", mergedOverview.decisions);
        pushEventFeed("action_item", mergedOverview.actionItems);
        pushEventFeed("risk", mergedOverview.risks);
    } catch (error) {
        console.warn("[CAPS] live event processing failed:", error, payload.events);
    }
}

function emitFinalizeMetrics(metrics) {
    if (!metrics) {
        return;
    }
    console.debug("[CAPS][live-metrics] finalize", metrics);
}
