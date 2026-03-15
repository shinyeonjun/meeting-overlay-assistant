import {
    clearMeetingContextSelection,
    getSelectedMeetingContextFilters,
    getSelectedMeetingContextSummary,
} from "../context-controller.js";
import { fetchHistoryTimeline } from "../../services/api/history-api.js";
import {
    listRecentReports,
    listSharedWithMeReports,
} from "../../services/api/report-api.js";
import { listSessions } from "../../services/api/meeting-session-api.js";
import {
    normalizeHistoryTimelinePayload,
    normalizeReportListPayload,
    normalizeSessionListPayload,
    normalizeSharedReportListPayload,
} from "../../services/payload-normalizers.js";
import { appState } from "../../state/app-state.js";
import {
    applyHistoryTimeline,
    applyHistorySnapshot,
    clearHistoryTimeline,
    resetHistoryState,
    setHistoryError,
    setHistoryLoading,
    setHistoryTimelineLoading,
} from "../../state/history-store.js";
import { refreshSelectedHistoryDetails } from "./detail-share-controller.js";
import { canUseShareFeatures, resolveEffectiveScope, TIMELINE_LIMIT } from "./helpers.js";
import { renderHistoryBoard } from "./history-render-controller.js";

export async function refreshHistoryBoard({ includeDetails = true } = {}) {
    const loaded = await loadHistoryBoard();
    if (!loaded) {
        return;
    }

    if (
        includeDetails
        && (
            appState.history.selectedKind === "report"
            || appState.history.selectedKind === "shared-report"
        )
    ) {
        void refreshSelectedHistoryDetails();
    }
}

export async function refreshHistorySnapshot() {
    await refreshHistoryBoard({ includeDetails: false });
}

export function resetHistoryBoard() {
    resetHistoryState(appState);
    renderHistoryBoard();
}

export function handleHistoryContextReset() {
    clearMeetingContextSelection();
    void refreshHistoryBoard();
}

async function loadHistoryBoard() {
    const scope = resolveEffectiveScope();
    const contextSummary = getSelectedMeetingContextSummary();
    const contextFilters = getSelectedMeetingContextFilters();

    setHistoryLoading(appState, true);
    setHistoryTimelineLoading(appState, contextSummary.hasSelection);
    renderHistoryBoard();

    try {
        const [sessionsPayload, reportsPayload, sharedReportsPayload, timelinePayload] = await Promise.all([
            listSessions({ scope, limit: 8, ...contextFilters }),
            listRecentReports({ scope, limit: 8, ...contextFilters }),
            canUseShareFeatures()
                ? listSharedWithMeReports({ limit: 8 })
                : Promise.resolve({ items: [] }),
            contextSummary.hasSelection
                ? fetchHistoryTimeline({ scope, limit: TIMELINE_LIMIT, ...contextFilters })
                : Promise.resolve(null),
        ]);

        applyHistorySnapshot(appState, {
            sessions: normalizeSessionListPayload(sessionsPayload),
            reports: normalizeReportListPayload(reportsPayload),
            sharedReports: normalizeSharedReportListPayload(sharedReportsPayload),
            effectiveScope: scope,
        });

        if (timelinePayload) {
            applyHistoryTimeline(appState, normalizeHistoryTimelinePayload(timelinePayload));
        } else {
            clearHistoryTimeline(appState);
        }

        renderHistoryBoard();
        return true;
    } catch (error) {
        console.error("[CAPS] 히스토리 목록 조회 실패:", error);
        clearHistoryTimeline(appState);
        setHistoryError(
            appState,
            "히스토리 목록을 불러오지 못했습니다. 서버 연결과 권한을 확인해 주세요.",
        );
        renderHistoryBoard();
        return false;
    }
}
