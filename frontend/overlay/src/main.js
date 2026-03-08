/**
 * 애플리케이션 진입점 — 컨트롤러 부트스트랩만 담당
 *
 * 모든 비즈니스 로직은 controllers/ 아래 파일에 위치한다.
 *   - ui-controller.js     : 드래그, 탭, 워크스페이스, Tauri 브리지
 *   - session-controller.js: 세션 생성, overview 폴링, 렌더링
 *   - live-controller.js   : 실시간 자막, WebSocket/Tauri 오디오, 피드
 *   - report-controller.js : 리포트 생성/조회, 경로 복사
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
    connectLiveSource,
    sendDevText,
} from "./controllers/live-controller.js";
import {
    handleGenerateReport,
    handleGeneratePdfReport,
    handleLoadLatestReport,
    handleRegenerateReports,
    copyReportPath,
    refreshReportFinalStatus,
    setupReportHistoryDelegation,
} from "./controllers/report-controller.js";
import {
    handleRefreshEvents,
    setupEventActionDelegation,
} from "./controllers/events-controller.js";
import { refreshReportHistory } from "./controllers/shared-rendering.js";

/* ───────────────────────────────── 초기화 ─── */

setupTauriUiBridge();
setupTauriLiveAudioBridge();
setupDraggableLayout();
setupEventActionDelegation();
setupReportHistoryDelegation();
setupDefaults();
bindEvents();
renderEmptyState();
refreshReportFinalStatus().catch((error) => {
    console.warn("[CAPS] 초기 리포트 상태 조회 실패:", error);
});

/* ───────────────────────────────── 이벤트 바인딩 ─── */

function bindEvents() {
    elements.closePanel.addEventListener("click", closeWorkspace);
    elements.captionToggle.addEventListener("click", toggleCaptionBody);

    for (const tab of elements.tabs) {
        tab.addEventListener("click", () => {
            activateTab(tab.dataset.tab);
            if (tab.dataset.tab === "events") {
                void handleRefreshEvents();
            }
            if (tab.dataset.tab === "report") {
                void refreshReportHistory();
            }
        });
    }

    elements.createSessionButton.addEventListener("click", handleCreateSession);
    elements.endSessionButton?.addEventListener("click", handleEndSession);
    elements.sessionSource.addEventListener("change", handleSessionSourceChange);
    elements.connectDevTextButton.addEventListener("click", connectLiveSource);
    elements.sendDevTextButton.addEventListener("click", sendDevText);
    elements.refreshEventsButton?.addEventListener("click", handleRefreshEvents);
    elements.generateReportButton.addEventListener("click", handleGenerateReport);
    elements.generatePdfReportButton?.addEventListener("click", handleGeneratePdfReport);
    elements.regenerateReportsButton?.addEventListener("click", handleRegenerateReports);
    elements.loadLatestReportButton?.addEventListener("click", handleLoadLatestReport);
    elements.openReportButton.addEventListener("click", copyReportPath);
}
