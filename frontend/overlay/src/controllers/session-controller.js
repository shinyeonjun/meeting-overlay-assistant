/**
 * 세션 컨트롤러
 * 세션 생성/종료, overview polling, runtime readiness, 경과 시간 표시를 담당한다.
 */

import {
    POLLING_INTERVAL_MS,
    RUNTIME_READINESS_POLLING_INTERVAL_MS,
} from "../config/constants.js";
import { DEFAULT_SESSION_TITLE } from "../config/defaults.js";
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
import { refreshReportFinalStatus } from "./report-controller.js";
import { openWorkspace, setStatus, flashStatus } from "./ui-controller.js";
import {
    refreshEventBoard,
    refreshOverview,
    refreshReportHistory,
    renderOverviewColumns,
    renderReportPanels,
} from "./shared-rendering.js";

let elapsedTimerId = null;
let runtimeReadinessTimerId = null;
const RUNTIME_READINESS_TIMER_KEY = "__capsRuntimeReadinessTimerId";
const RUNTIME_READINESS_TIMER_SET_KEY = "__capsRuntimeReadinessTimerIds";
const RUNTIME_READINESS_IN_FLIGHT_KEY = "__capsRuntimeReadinessInFlight";

export function setupDefaults() {
    elements.sessionTitle.value = DEFAULT_SESSION_TITLE;
    if (elements.reportFormatSelect) {
        elements.reportFormatSelect.value = "pdf";
    }
    clearCurrentUtterance(appState);
    renderCurrentUtterance();
    renderRuntimeReadiness();
    if (!isSessionActive()) {
        startRuntimeReadinessPolling();
    }
}

export function renderEmptyState() {
    renderOverviewColumns();
    renderReportPanels();
}

export async function handleCreateSession() {
    const title = elements.sessionTitle.value.trim();
    const source = elements.sessionSource.value;

    if (!title) {
        flashStatus(elements.sessionStatus, "제목이 필요합니다.", "error");
        return;
    }

    if (!appState.runtime.startReady) {
        await refreshRuntimeReadiness();
        flashStatus(elements.sessionStatus, "준비가 끝난 뒤 다시 시도해 주세요.", "error");
        return;
    }

    await stopActiveLiveConnection();
    setStatus(elements.sessionStatus, "세션 생성 중", "idle");

    try {
        const sessionPayload = normalizeSessionPayload(await createSession({ title, source }));
        setSession(appState, sessionPayload);

        appState.report.latestReportId = null;
        appState.report.latestReportType = null;
        appState.report.latestVersion = null;
        appState.report.latestPath = null;
        appState.report.status = "idle";
        elements.reportFilePath.textContent = "";
        elements.reportVersion.textContent = "-";
        setStatus(elements.reportStatus, "생성 대기", "idle");

        elements.sessionId.textContent = sessionPayload.id;
        if (elements.sessionActiveSources) {
            elements.sessionActiveSources.textContent = sessionPayload.actualActiveSources.join(", ") || "-";
        }
        elements.sessionInfo.classList.remove("hidden");
        setStatus(elements.sessionStatus, "진행 중", "live");
        stopRuntimeReadinessPolling();

        openWorkspace();
        startOverviewPolling();
        startElapsedTimer();
        refreshReportFinalStatus().catch((error) => {
            console.warn("[CAPS] 리포트 상태 조회 실패:", error);
        });

        connectLiveSource().catch((error) => {
            console.warn("[CAPS] 자동 연결 실패:", error);
        });
    } catch (error) {
        console.error(error);
        setStatus(elements.sessionStatus, "세션 생성 실패", "error");
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
        const sessionPayload = normalizeSessionPayload(await endSession(appState.session.id));
        setSession(appState, sessionPayload);
        stopOverviewPolling();
        stopElapsedTimer();

        if (elements.sessionActiveSources) {
            elements.sessionActiveSources.textContent = sessionPayload.actualActiveSources.join(", ") || "-";
        }

        await refreshOverview();
        await refreshEventBoard();
        await refreshReportHistory();
        setStatus(elements.sessionStatus, "종료됨", "live");
        setStatus(elements.reportStatus, "생성 대기", "idle");
        startRuntimeReadinessPolling();
    } catch (error) {
        console.error(error);
        setStatus(elements.sessionStatus, "세션 종료 실패", "error");
    }
}

export function startOverviewPolling() {
    stopOverviewPolling();
    refreshOverview();
    refreshEventBoard();
    setSessionTimer(appState, window.setInterval(refreshOverview, POLLING_INTERVAL_MS));
}

export function stopOverviewPolling() {
    clearSessionTimer(appState);
}

export async function refreshRuntimeReadiness() {
    if (isSessionActive()) {
        stopRuntimeReadinessPolling();
        return;
    }

    if (window[RUNTIME_READINESS_IN_FLIGHT_KEY]) {
        return;
    }

    window[RUNTIME_READINESS_IN_FLIGHT_KEY] = true;
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
    } finally {
        window[RUNTIME_READINESS_IN_FLIGHT_KEY] = false;
    }

    renderRuntimeReadiness();
}

export function handleSessionSourceChange() {
    void refreshRuntimeReadiness();
}

function startRuntimeReadinessPolling() {
    stopRuntimeReadinessPolling();
    if (isSessionActive()) {
        return;
    }
    void refreshRuntimeReadiness();
    runtimeReadinessTimerId = window.setInterval(() => {
        void refreshRuntimeReadiness();
    }, RUNTIME_READINESS_POLLING_INTERVAL_MS);
    window[RUNTIME_READINESS_TIMER_KEY] = runtimeReadinessTimerId;
    const timerIds = getRuntimeReadinessTimerIds();
    timerIds.add(runtimeReadinessTimerId);
}

function stopRuntimeReadinessPolling() {
    const timerIds = getRuntimeReadinessTimerIds();
    for (const timerId of timerIds) {
        window.clearInterval(timerId);
    }
    timerIds.clear();
    runtimeReadinessTimerId = null;
    window[RUNTIME_READINESS_TIMER_KEY] = null;
    window[RUNTIME_READINESS_IN_FLIGHT_KEY] = false;
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

function isSessionActive() {
    return Boolean(appState.session.id) && appState.session.status !== "ended";
}

function getRuntimeReadinessTimerIds() {
    if (!(window[RUNTIME_READINESS_TIMER_SET_KEY] instanceof Set)) {
        window[RUNTIME_READINESS_TIMER_SET_KEY] = new Set();
    }
    return window[RUNTIME_READINESS_TIMER_SET_KEY];
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

function stopElapsedTimer() {
    if (elapsedTimerId !== null) {
        window.clearInterval(elapsedTimerId);
        elapsedTimerId = null;
    }
}

export { renderOverviewColumns, renderReportPanels, refreshOverview };
