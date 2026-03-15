/**
 * 애플리케이션 진입점.
 * 인증 게이트를 통과한 뒤 세션, 이벤트, 리포트, 히스토리 흐름을 초기화한다.
 */

import { elements } from "./dom/elements.js";
import {
    refreshMeetingContextOptions,
    setupContextControls,
} from "./controllers/context-controller.js";
import {
    setupTauriUiBridge,
    setupDraggableLayout,
    activateTab,
    closeWorkspace,
    toggleCaptionBody,
} from "./controllers/ui-controller.js";
import {
    renderWorkflowSummary,
    setupWorkflowSummary,
} from "./controllers/ui/workflow-summary-controller.js";
import { initializeAuthFlow } from "./controllers/auth-controller.js";
import {
    setupDefaults,
    handleSessionSourceChange,
} from "./controllers/runtime-controller.js";
import {
    refreshHistoryBoard,
    setupHistoryControls,
} from "./controllers/history-controller.js";
import {
    renderEmptyState,
    handleCreateSession,
    handleStartSession,
    handleEndSession,
} from "./controllers/session-controller.js";
import { setupTauriLiveAudioBridge } from "./controllers/live-controller.js";
import {
    handleGenerateReport,
    refreshReportFinalStatus,
} from "./controllers/report-controller.js";
import {
    handleRefreshEvents,
    setupEventActionDelegation,
} from "./controllers/events-controller.js";

let workspaceInitialized = false;

void startApplication();

async function startApplication() {
    setupTauriUiBridge();
    setupDraggableLayout();
    bindEvents();
    await initializeAuthFlow({
        onReady: handleWorkspaceReady,
    });
}

function handleWorkspaceReady() {
    ensureWorkspaceInitialized();
    void refreshHistoryBoard();
    void refreshMeetingContextOptions();
}

function ensureWorkspaceInitialized() {
    if (workspaceInitialized) {
        return;
    }

    workspaceInitialized = true;
    void setupTauriLiveAudioBridge();
    setupEventActionDelegation();
    setupHistoryControls();
    setupContextControls();
    setupWorkflowSummary();
    setupDefaults();
    renderEmptyState();
    renderWorkflowSummary();
    refreshReportFinalStatus().catch((error) => {
        console.warn("[CAPS] 초기 리포트 상태 조회 실패:", error);
    });
}

function bindEvents() {
    elements.closePanel.addEventListener("click", closeWorkspace);
    elements.captionToggle.addEventListener("click", toggleCaptionBody);

    for (const tab of elements.tabs) {
        tab.addEventListener("click", () => {
            activateTab(tab.dataset.tab);
            renderWorkflowSummary();
            if (tab.dataset.tab === "events") {
                void handleRefreshEvents();
            }
            if (tab.dataset.tab === "report") {
                void refreshReportFinalStatus();
            }
            if (tab.dataset.tab === "history") {
                void refreshHistoryBoard();
            }
        });
    }

    elements.createSessionButton.addEventListener("click", handleCreateSession);
    elements.startSessionButton?.addEventListener("click", handleStartSession);
    elements.endSessionButton?.addEventListener("click", handleEndSession);
    elements.sessionSource.addEventListener("change", handleSessionSourceChange);
    elements.refreshEventsButton?.addEventListener("click", handleRefreshEvents);
    elements.generateReportButton?.addEventListener("click", handleGenerateReport);
}
