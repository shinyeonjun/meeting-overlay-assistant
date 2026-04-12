import { elements } from "../../dom/elements.js";
import {
    createSession,
    endSession,
    startSession,
} from "../../services/api/meeting-session-api.js";
import { normalizeSessionPayload } from "../../services/payload-normalizers.js";
import { appState } from "../../state/app-state.js";
import { setSession, setSessionParticipants } from "../../state/session/meeting-session-store.js";
import { getSelectedMeetingContextRequest } from "../context-controller.js";
import { renderEventBoard } from "../events-board-controller.js";
import { refreshHistorySnapshot } from "../history-controller.js";
import { connectLiveSource, stopActiveLiveConnection } from "../live-controller.js";
import { refreshReportFinalStatus } from "../report-controller.js";
import {
    refreshRuntimeReadiness,
    startRuntimeReadinessPolling,
    stopRuntimeReadinessPolling,
} from "../runtime-controller.js";
import { flashStatus, openWorkspace, setStatus } from "../ui-controller.js";
import {
    bindParticipantCandidateEvents,
    parseSessionParticipants,
    refreshSessionParticipationState,
    renderParticipantCandidates,
} from "../participation/participation-resolution-controller.js";
import {
    refreshSessionOverviewAndBoard,
    startOverviewPolling,
    stopOverviewPolling,
} from "./session-runtime-controller.js";
import { renderSessionSummary, resetReportState } from "./session-summary-renderer.js";
import { startElapsedTimer, stopElapsedTimer } from "./session-timer.js";

export function renderEmptyState() {
    renderEventBoard();
    renderParticipantCandidates();
    renderSessionSummary();
}

export async function handleCreateSession() {
    const title = elements.sessionTitle.value.trim();
    const primaryInputSource = elements.sessionSource.value;
    const participantsText = elements.sessionParticipants?.value.trim() ?? "";
    const participants = parseSessionParticipants(participantsText);
    const meetingContext = getSelectedMeetingContextRequest();

    if (!title) {
        flashStatus(elements.sessionStatus, "세션 제목이 필요합니다.", "error");
        return;
    }

    if (appState.session.id && appState.session.status !== "ended") {
        flashStatus(
            elements.sessionStatus,
            "기존 세션을 종료한 뒤 새 세션을 만들 수 있습니다.",
            "error",
        );
        return;
    }

    setStatus(elements.sessionStatus, "세션 준비 중", "idle");

    try {
        const sessionPayload = normalizeSessionPayload(
            await createSession({
                title,
                primaryInputSource,
                participants,
                ...meetingContext,
            }),
        );

        setSession(appState, sessionPayload);
        setSessionParticipants(appState, participantsText);
        resetReportState();
        stopOverviewPolling();
        stopElapsedTimer();

        elements.sessionInfo?.classList.remove("hidden");
        bindParticipantCandidateEvents();
        await refreshSessionParticipationState(sessionPayload.id);
        openWorkspace();

        startRuntimeReadinessPolling();
        await refreshRuntimeReadiness();
        refreshHistorySnapshot().catch((error) => {
            console.warn("[CAPS] 히스토리 갱신 실패:", error);
        });

        setStatus(elements.sessionStatus, "준비됨", "idle");
    } catch (error) {
        console.error(error);
        setStatus(elements.sessionStatus, "세션 생성 실패", "error");
    }
}

export async function handleStartSession() {
    if (!appState.session.id) {
        flashStatus(elements.sessionStatus, "먼저 세션을 만들어 주세요.", "error");
        return;
    }

    if (appState.session.status === "running") {
        flashStatus(elements.sessionStatus, "이미 진행 중인 세션입니다.", "live");
        return;
    }

    if (!appState.runtime.startReady) {
        await refreshRuntimeReadiness();
        flashStatus(
            elements.sessionStatus,
            "준비가 끝난 뒤 다시 시작해 주세요.",
            "error",
        );
        return;
    }

    setStatus(elements.sessionStatus, "회의 시작 중", "idle");

    try {
        const sessionPayload = normalizeSessionPayload(
            await startSession(appState.session.id),
        );
        setSession(appState, sessionPayload);
        await refreshSessionParticipationState(sessionPayload.id);
        stopRuntimeReadinessPolling();
        openWorkspace();
        startOverviewPolling();
        startElapsedTimer();

        refreshReportFinalStatus().catch((error) => {
            console.warn("[CAPS] 리포트 상태 조회 실패:", error);
        });
        refreshHistorySnapshot().catch((error) => {
            console.warn("[CAPS] 히스토리 갱신 실패:", error);
        });

        connectLiveSource().catch((error) => {
            console.warn("[CAPS] 자동 연결 실패:", error);
        });
        setStatus(elements.sessionStatus, "진행 중", "live");
    } catch (error) {
        console.error(error);
        setStatus(elements.sessionStatus, "회의 시작 실패", "error");
    }
}

export async function handleEndSession() {
    if (!appState.session.id) {
        flashStatus(elements.sessionStatus, "세션이 없습니다.", "error");
        return;
    }

    setStatus(elements.sessionStatus, "세션 종료 중", "idle");

    try {
        await stopActiveLiveConnection();
        const sessionPayload = normalizeSessionPayload(
            await endSession(appState.session.id),
        );
        setSession(appState, sessionPayload);
        stopOverviewPolling();
        stopElapsedTimer();

        await refreshSessionParticipationState(sessionPayload.id);
        await Promise.all([
            refreshSessionOverviewAndBoard(),
            refreshHistorySnapshot(),
        ]);

        setStatus(elements.sessionStatus, "종료됨", "idle");
        setStatus(elements.reportStatus, "생성 대기", "idle");
        startRuntimeReadinessPolling();
    } catch (error) {
        console.error(error);
        setStatus(elements.sessionStatus, "세션 종료 실패", "error");
    }
}

export { startOverviewPolling, stopOverviewPolling };
