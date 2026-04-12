/** 오버레이 런타임의 start application 모듈이다. */
import { elements } from "../dom/elements.js";
import { initializeAuthFlow } from "../features/auth/index.js";
import {
    refreshMeetingContextOptions,
    setupContextControls,
} from "../features/context/index.js";
import {
    handleRefreshEvents,
    setupEventActionDelegation,
} from "../features/events/index.js";
import { setupTauriLiveAudioBridge } from "../features/live/index.js";
import { refreshReportFinalStatus } from "../features/report/index.js";
import {
    handleSessionSourceChange,
    setupDefaults,
} from "../features/runtime/index.js";
import {
    handleCreateSession,
    handleEndSession,
    handleStartSession,
    renderEmptyState,
} from "../features/session/index.js";
import {
    activateTab,
    closeWorkspace,
    openWebWorkspace,
    renderWorkflowSummary,
    setupDraggableLayout,
    setupTauriUiBridge,
    setupWorkflowSummary,
    toggleCaptionBody,
} from "../features/workspace/index.js";

let workspaceInitialized = false;

export async function startApplication() {
    setupTauriUiBridge();
    setupDraggableLayout();
    bindEvents();
    await initializeAuthFlow({
        onReady: handleWorkspaceReady,
    });
}

function handleWorkspaceReady() {
    ensureWorkspaceInitialized();
    void refreshMeetingContextOptions();
}

function ensureWorkspaceInitialized() {
    if (workspaceInitialized) {
        return;
    }

    workspaceInitialized = true;
    void setupTauriLiveAudioBridge();
    setupEventActionDelegation();
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
    elements.closePanel?.addEventListener("click", closeWorkspace);
    elements.captionToggle?.addEventListener("click", toggleCaptionBody);

    for (const tab of elements.tabs) {
        tab.addEventListener("click", () => {
            activateTab(tab.dataset.tab);
            renderWorkflowSummary();
            if (tab.dataset.tab === "events") {
                void handleRefreshEvents();
            }
        });
    }

    elements.createSessionButton?.addEventListener("click", handleCreateSession);
    elements.startSessionButton?.addEventListener("click", handleStartSession);
    elements.endSessionButton?.addEventListener("click", handleEndSession);
    elements.sessionSource?.addEventListener("change", handleSessionSourceChange);
    elements.refreshEventsButton?.addEventListener("click", handleRefreshEvents);
    elements.openWebWorkspaceButton?.addEventListener("click", () => {
        openWebWorkspace("overview");
    });
    elements.openWebReportsButton?.addEventListener("click", () => {
        openWebWorkspace("reports");
    });
    elements.openWebHistoryButton?.addEventListener("click", () => {
        openWebWorkspace("history");
    });
    elements.openWebAssistantButton?.addEventListener("click", () => {
        openWebWorkspace("assistant");
    });
}
