/**
 * 런타임 컨트롤러
 * 세션 시작 전 readiness 확인과 운영 모니터 지표 polling을 맡는다.
 */

import { isClientSourceReady } from "../audio/source-policy.js";
import { DEFAULT_SESSION_TITLE } from "../config/defaults.js";
import { RUNTIME_READINESS_POLLING_INTERVAL_MS } from "../config/constants.js";
import { elements } from "../dom/elements.js";
import {
    fetchRuntimeMonitor,
    fetchRuntimeReadiness,
} from "../services/api/runtime-api.js";
import {
    normalizeRuntimeMonitorPayload,
    normalizeRuntimeReadinessPayload,
} from "../services/payload-normalizers.js";
import { appState } from "../state/app-state.js";
import { clearCurrentUtterance } from "../state/live-store.js";
import {
    applyRuntimeMonitor,
    applyRuntimeReadiness,
    clearRuntimeMonitor,
    setBridgeReady,
} from "../state/runtime-store.js";
import {
    ensureTauriLiveAudioPrewarmed,
    setupTauriLiveAudioBridge,
} from "./live-controller.js";
import { renderCurrentUtterance } from "./live/live-caption-renderer.js";
import { setStatus } from "./ui-controller.js";
import { renderWorkflowSummary } from "./ui/workflow-summary-controller.js";

let runtimeReadinessTimerId = null;
let runtimeReadinessInFlight = false;

export function setupDefaults() {
    elements.sessionTitle.value = DEFAULT_SESSION_TITLE;

    clearCurrentUtterance(appState);
    renderCurrentUtterance();
    renderRuntimeReadiness();
    renderRuntimeMonitor();
    renderWorkflowSummary();

    if (!isSessionActive()) {
        startRuntimeReadinessPolling();
    }
}

export async function refreshRuntimeReadiness() {
    if (isSessionActive()) {
        stopRuntimeReadinessPolling();
        return;
    }

    if (runtimeReadinessInFlight) {
        return;
    }

    runtimeReadinessInFlight = true;
    const selectedSource = elements.sessionSource.value;
    const bridgeReady = await setupTauriLiveAudioBridge();
    setBridgeReady(appState, bridgeReady, selectedSource);
    void ensureTauriLiveAudioPrewarmed(selectedSource);

    try {
        const [readinessPayload, monitorPayload] = await Promise.all([
            fetchRuntimeReadiness(),
            fetchRuntimeMonitor(),
        ]);
        applyRuntimeReadiness(
            appState,
            normalizeRuntimeReadinessPayload(readinessPayload),
            selectedSource,
        );
        applyRuntimeMonitor(appState, normalizeRuntimeMonitorPayload(monitorPayload));
    } catch (error) {
        console.error(error);
        appState.runtime.serverReady = false;
        appState.runtime.sttReady = false;
        appState.runtime.warming = true;
        appState.runtime.selectedSource = selectedSource;
        appState.runtime.selectedSourceReady = false;
        appState.runtime.startReady = false;
        clearRuntimeMonitor(appState);
    } finally {
        runtimeReadinessInFlight = false;
    }

    renderRuntimeReadiness();
    renderRuntimeMonitor();
    renderWorkflowSummary();
}

export function handleSessionSourceChange() {
    void refreshRuntimeReadiness();
}

export function startRuntimeReadinessPolling() {
    stopRuntimeReadinessPolling();
    if (isSessionActive()) {
        return;
    }

    void refreshRuntimeReadiness();
    runtimeReadinessTimerId = window.setInterval(() => {
        void refreshRuntimeReadiness();
    }, RUNTIME_READINESS_POLLING_INTERVAL_MS);
}

export function stopRuntimeReadinessPolling() {
    if (runtimeReadinessTimerId !== null) {
        window.clearInterval(runtimeReadinessTimerId);
        runtimeReadinessTimerId = null;
    }
    runtimeReadinessInFlight = false;
}

function renderRuntimeReadiness() {
    const selectedSource = elements.sessionSource.value;
    const clientReady = isClientSourceReady(
        selectedSource,
        appState.runtime.preloadedSources,
        appState.runtime.bridgeReady,
    );
    const overallTone = appState.runtime.startReady
        ? "live"
        : (appState.runtime.warming ? "idle" : "error");
    const overallText = appState.runtime.startReady
        ? "ready"
        : (appState.runtime.warming ? "warming" : "blocked");

    setStatus(elements.runtimeOverall, overallText, overallTone);
    setStatus(elements.runtimeClient, clientReady ? "client ready" : "client wait", clientReady ? "live" : "idle");
    setStatus(elements.runtimeServer, appState.runtime.serverReady ? "server ready" : "server wait", appState.runtime.serverReady ? "live" : "idle");
    setStatus(
        elements.runtimeStt,
        appState.runtime.selectedSourceReady ? `${selectedSource} ready` : `${selectedSource} wait`,
        appState.runtime.selectedSourceReady ? "live" : "idle",
    );

    if (elements.createSessionButton) {
        elements.createSessionButton.disabled = false;
    }
    if (elements.startSessionButton) {
        const canStart =
            appState.session.status === "draft"
            && Boolean(appState.session.id)
            && appState.runtime.startReady;
        elements.startSessionButton.disabled = !canStart;
    }
    renderWorkflowSummary();
}

function renderRuntimeMonitor() {
    const monitor = appState.runtime.monitor;
    setMetricText(elements.monitorActiveSessions, `${monitor.activeSessionCount}건`);
    setMetricText(elements.monitorAvgDelay, formatMilliseconds(monitor.averageQueueDelayMs));
    setMetricText(elements.monitorMaxDelay, formatMilliseconds(monitor.maxQueueDelayMs));
    setMetricText(elements.monitorLateFinals, `${monitor.lateFinalCount}회`);
    setMetricText(elements.monitorBackpressure, `${monitor.backpressureCount}회`);
    setMetricText(
        elements.monitorThroughput,
        `발화 ${monitor.recentUtteranceCount} / 이벤트 ${monitor.recentEventCount}`,
    );
    setMetricText(elements.monitorLastProcessed, formatTimestamp(monitor.lastChunkProcessedAt));
    setMetricText(
        elements.monitorLastError,
        monitor.lastErrorMessage || "최근 오류 없음",
    );
}

function setMetricText(element, text) {
    if (!element) {
        return;
    }
    element.textContent = text;
}

function formatMilliseconds(value) {
    if (value === null || value === undefined) {
        return "-";
    }
    return `${Math.round(value)}ms`;
}

function formatTimestamp(value) {
    if (!value) {
        return "-";
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return "-";
    }
    return new Intl.DateTimeFormat("ko-KR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
    }).format(parsed);
}

function isSessionActive() {
    return Boolean(appState.session.id) && appState.session.status === "running";
}
