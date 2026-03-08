/**
 * 세션 컨트롤러 — 세션 생성, overview 폴링, 기본값 설정, 경과 시간
 */

import {
    POLLING_INTERVAL_MS,
    RUNTIME_READINESS_POLLING_INTERVAL_MS,
} from "../config/constants.js";
import { DEFAULT_SESSION_TITLE, DEFAULT_REPORT_AUDIO_PATH } from "../config/defaults.js";
import { elements } from "../dom/elements.js";
import { createSession, endSession, fetchRuntimeReadiness } from "../services/api-client.js";
import { normalizeSessionPayload } from "../services/payload-normalizers.js";
import { appState } from "../state/app-state.js";
import { clearCurrentUtterance } from "../state/live-store.js";
import { applyRuntimeReadiness, setBridgeReady } from "../state/runtime-store.js";
import { clearSessionTimer, setSession, setSessionTimer } from "../state/session-store.js";
import {
    connectLiveSource,
    setupTauriLiveAudioBridge,
    stopActiveLiveConnection,
} from "./live-controller.js";
import { renderCurrentUtterance } from "./live/live-caption-renderer.js";
import {
    handleLoadLatestReport,
    refreshReportFinalStatus,
} from "./report-controller.js";
import { openWorkspace, setStatus, flashStatus } from "./ui-controller.js";
import {
    refreshEventBoard,
    refreshOverview,
    refreshReportHistory,
    renderOverviewColumns,
    renderReportPanels,
} from "./shared-rendering.js";

/** 경과 시간 타이머 ID */
let elapsedTimerId = null;
let runtimeReadinessTimerId = null;
const RUNTIME_READINESS_TIMER_KEY = "__capsRuntimeReadinessTimerId";

/* ───────────────────────────────── 초기 설정 ─── */

/** 기본값을 폼 요소에 세팅한다. */
export function setupDefaults() {
    elements.sessionTitle.value = DEFAULT_SESSION_TITLE;
    elements.reportAudioPath.value = DEFAULT_REPORT_AUDIO_PATH;
    clearCurrentUtterance(appState);
    renderCurrentUtterance();
    renderRuntimeReadiness();
    startRuntimeReadinessPolling();
}

/** 빈 상태 UI를 렌더링한다. */
export function renderEmptyState() {
    renderOverviewColumns();
    renderReportPanels();
}

/* ───────────────────────────────── 세션 생성 ─── */

/** 새 세션을 생성하고 라이브 연결 + 폴링을 시작한다. */
export async function handleCreateSession() {
    const title = elements.sessionTitle.value.trim();
    const source = elements.sessionSource.value;

    if (!title) {
        flashStatus(elements.sessionStatus, "제목 필요", "error");
        return;
    }

    if (!appState.runtime.startReady) {
        await refreshRuntimeReadiness();
        flashStatus(elements.sessionStatus, "준비 완료 후 시작할 수 있습니다.", "error");
        return;
    }

    await stopActiveLiveConnection();
    setStatus(elements.sessionStatus, "생성 중", "idle");

    try {
        const sessionPayload = normalizeSessionPayload(await createSession({ title, source }));
        setSession(appState, sessionPayload);

        elements.sessionId.textContent = sessionPayload.id;
        if (elements.sessionActiveSources) {
            elements.sessionActiveSources.textContent = sessionPayload.actualActiveSources.join(", ") || "-";
        }
        elements.sessionInfo.classList.remove("hidden");
        setStatus(elements.sessionStatus, "실행 중", "live");
        stopRuntimeReadinessPolling();

        openWorkspace();
        startOverviewPolling();
        startElapsedTimer();
        refreshReportFinalStatus().catch((error) => {
            console.warn("[CAPS] 리포트 상태 조회 실패:", error);
        });

        /* 세션 생성 후 자동 연결 */
        connectLiveSource().catch((error) => {
            console.warn("[CAPS] 자동 연결 실패:", error);
        });
    } catch (error) {
        console.error(error);
        setStatus(elements.sessionStatus, "생성 실패", "error");
    }
}

/** 현재 세션을 종료하고 자동 생성된 최종 리포트를 반영한다. */
export async function handleEndSession() {
    if (!appState.session.id) {
        flashStatus(elements.sessionStatus, "세션 필요", "error");
        return;
    }

    setStatus(elements.sessionStatus, "종료 중", "idle");

    try {
        const sessionPayload = normalizeSessionPayload(await endSession(appState.session.id));
        setSession(appState, sessionPayload);
        await stopActiveLiveConnection();
        stopOverviewPolling();
        stopElapsedTimer();

        if (elements.sessionActiveSources) {
            elements.sessionActiveSources.textContent = sessionPayload.actualActiveSources.join(", ") || "-";
        }

        await refreshOverview();
        await refreshEventBoard();
        await refreshReportHistory();
        await refreshReportFinalStatus();
        await handleLoadLatestReport();
        startRuntimeReadinessPolling();
        setStatus(elements.sessionStatus, "종료됨", "live");
    } catch (error) {
        console.error(error);
        setStatus(elements.sessionStatus, "종료 실패", "error");
    }
}

/* ───────────────────────────────── overview 폴링 ─── */

/** overview 폴링을 시작한다. */
export function startOverviewPolling() {
    stopOverviewPolling();
    refreshOverview();
    refreshEventBoard();
    setSessionTimer(appState, window.setInterval(refreshOverview, POLLING_INTERVAL_MS));
}

/** overview 폴링을 중지한다. */
export function stopOverviewPolling() {
    clearSessionTimer(appState);
}

/* ───────────────────────────────── 경과 시간 타이머 ─── */

/** 세션 경과 시간 타이머를 시작한다. */
export async function refreshRuntimeReadiness() {
    const selectedSource = elements.sessionSource.value;
    const bridgeReady = await setupTauriLiveAudioBridge();
    setBridgeReady(appState, bridgeReady, selectedSource);

    try {
        const payload = await fetchRuntimeReadiness();
        applyRuntimeReadiness(appState, payload, selectedSource);
    } catch (error) {
        console.error(error);
        appState.runtime.backendReady = false;
        appState.runtime.sttReady = false;
        appState.runtime.warming = true;
        appState.runtime.selectedSource = selectedSource;
        appState.runtime.selectedSourceReady = false;
        appState.runtime.startReady = false;
    }

    renderRuntimeReadiness();
}

export function handleSessionSourceChange() {
    void refreshRuntimeReadiness();
}

function startRuntimeReadinessPolling() {
    stopRuntimeReadinessPolling();
    void refreshRuntimeReadiness();
    runtimeReadinessTimerId = window.setInterval(() => {
        void refreshRuntimeReadiness();
    }, RUNTIME_READINESS_POLLING_INTERVAL_MS);
    window[RUNTIME_READINESS_TIMER_KEY] = runtimeReadinessTimerId;
}

function stopRuntimeReadinessPolling() {
    const timerId = runtimeReadinessTimerId ?? window[RUNTIME_READINESS_TIMER_KEY] ?? null;
    if (timerId !== null) {
        window.clearInterval(timerId);
        runtimeReadinessTimerId = null;
        window[RUNTIME_READINESS_TIMER_KEY] = null;
    }
}

function renderRuntimeReadiness() {
    const selectedSource = elements.sessionSource.value;
    const frontendReady = appState.runtime.bridgeReady || selectedSource === "mic" || selectedSource === "file";
    const overallTone = appState.runtime.startReady
        ? "live"
        : (appState.runtime.warming ? "idle" : "error");
    const overallText = appState.runtime.startReady
        ? "ready"
        : (appState.runtime.warming ? "warming" : "blocked");

    setStatus(elements.runtimeOverall, overallText, overallTone);
    setStatus(elements.runtimeFrontend, frontendReady ? "frontend ready" : "frontend wait", frontendReady ? "live" : "idle");
    setStatus(elements.runtimeBackend, appState.runtime.backendReady ? "backend ready" : "backend wait", appState.runtime.backendReady ? "live" : "idle");
    setStatus(
        elements.runtimeStt,
        appState.runtime.selectedSourceReady ? `${selectedSource} ready` : `${selectedSource} wait`,
        appState.runtime.selectedSourceReady ? "live" : "idle",
    );

    elements.createSessionButton.disabled = !appState.runtime.startReady;
}

function startElapsedTimer() {
    stopElapsedTimer();

    const timerEl = document.querySelector("#session-elapsed");
    if (!timerEl) {
        return;
    }

    const startTime = Date.now();

    const tick = () => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const minutes = String(Math.floor(elapsed / 60)).padStart(2, "0");
        const seconds = String(elapsed % 60).padStart(2, "0");
        timerEl.textContent = `${minutes}:${seconds}`;
    };

    tick();
    elapsedTimerId = window.setInterval(tick, 1000);
}

/** 경과 시간 타이머를 중지한다. */
function stopElapsedTimer() {
    if (elapsedTimerId !== null) {
        window.clearInterval(elapsedTimerId);
        elapsedTimerId = null;
    }
}

// refreshOverview, renderOverviewColumns, renderReportPanels → shared-rendering.js에서 제공
export { renderOverviewColumns, renderReportPanels, refreshOverview };
