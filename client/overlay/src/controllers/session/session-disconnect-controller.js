import { elements } from "../../dom/elements.js";
import { appState } from "../../state/app-state.js";
import { setSession } from "../../state/session/meeting-session-store.js";
import { flashStatus } from "../ui-controller.js";
import { renderEventBoard } from "../events-board-controller.js";
import { stopOverviewPolling } from "./session-runtime-controller.js";
import { renderSessionSummary } from "./session-summary-renderer.js";
import { stopElapsedTimer } from "./session-timer.js";

let disconnectHandlingPromise = null;

function buildLocallyEndedSessionPayload() {
    return {
        id: appState.session.id,
        title: appState.session.title,
        status: "ended",
        startedAt: appState.session.startedAt,
        endedAt: new Date().toISOString(),
        accountId: appState.session.accountId,
        contactId: appState.session.contactId,
        contextThreadId: appState.session.contextThreadId,
        participants: appState.session.participants,
        participantLinks: appState.session.participantLinks,
        participantCandidates: appState.session.participantCandidates,
        participantFollowups: appState.session.participantFollowups,
        participationSummary: appState.session.participationSummary,
        primaryInputSource: appState.session.primaryInputSource,
        actualActiveSources: [],
    };
}

export async function finalizeSessionLocallyAfterDisconnect({
    reason = "서버 연결이 끊겨 세션을 종료 처리했습니다.",
} = {}) {
    if (!appState.session.id || appState.session.status !== "running") {
        return;
    }

    if (disconnectHandlingPromise) {
        return disconnectHandlingPromise;
    }

    disconnectHandlingPromise = (async () => {
        stopOverviewPolling();
        stopElapsedTimer();

        try {
            const { stopActiveLiveConnection } = await import("../live-controller.js");
            await stopActiveLiveConnection();
        } catch (error) {
            console.warn("[CAPS] 연결 끊김 후 live 정리 실패:", error);
        }

        setSession(appState, buildLocallyEndedSessionPayload());
        renderSessionSummary();
        renderEventBoard();

        const {
            refreshRuntimeReadiness,
            startRuntimeReadinessPolling,
        } = await import("../runtime-controller.js");
        startRuntimeReadinessPolling();
        void refreshRuntimeReadiness();

        flashStatus(elements.sessionStatus, "서버 종료로 세션을 종료 처리했습니다.", "error");
        flashStatus(elements.liveConnectionStatus, reason, "error");
    })();

    try {
        await disconnectHandlingPromise;
    } finally {
        disconnectHandlingPromise = null;
    }
}
