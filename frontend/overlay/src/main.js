/**
 * 애플리케이션 진입점
 * 각 컨트롤러를 초기화하고 이벤트를 바인딩한다.
 */

import { elements } from "./dom/elements.js";
import {
    setupTauriUiBridge,
    setupDraggableLayout,
    activateTab,
    closeWorkspace,
    toggleCaptionBody,
} from "./controllers/ui-controller.js";
import {
    setupDefaults,
    renderEmptyState,
    handleCreateSession,
    handleEndSession,
    handleSessionSourceChange,
} from "./controllers/session-controller.js";
import {
    setupTauriLiveAudioBridge,
} from "./controllers/live-controller.js";
import {
    handleGenerateReport,
    refreshReportFinalStatus,
} from "./controllers/report-controller.js";
import {
    handleRefreshEvents,
    setupEventActionDelegation,
} from "./controllers/events-controller.js";

setupTauriUiBridge();
setupTauriLiveAudioBridge();
setupDraggableLayout();
setupEventActionDelegation();
setupDefaults();
bindEvents();
renderEmptyState();
refreshReportFinalStatus().catch((error) => {
    console.warn("[CAPS] 초기 리포트 상태 조회 실패:", error);
});

function bindEvents() {
    elements.closePanel.addEventListener("click", closeWorkspace);
    elements.captionToggle.addEventListener("click", toggleCaptionBody);

    for (const tab of elements.tabs) {
        tab.addEventListener("click", () => {
            activateTab(tab.dataset.tab);
            if (tab.dataset.tab === "events") {
                void handleRefreshEvents();
            }
        });
    }

    elements.createSessionButton.addEventListener("click", handleCreateSession);
    elements.endSessionButton?.addEventListener("click", handleEndSession);
    elements.sessionSource.addEventListener("change", handleSessionSourceChange);
    elements.refreshEventsButton?.addEventListener("click", handleRefreshEvents);
    elements.generateReportButton?.addEventListener("click", handleGenerateReport);
}
