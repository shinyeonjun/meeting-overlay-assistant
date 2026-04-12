import { elements } from "../../dom/elements.js";
import { appState } from "../../state/app-state.js";
import { setStatus } from "../ui-controller.js";
import { renderWorkflowSummary } from "../ui/workflow-summary-controller.js";

export function renderSessionSummary() {
    if (!elements.sessionInfo || !elements.sessionStatus) {
        return;
    }

    if (!appState.session.id) {
        elements.sessionInfo.classList.add("hidden");
        if (elements.endSessionButton) {
            elements.endSessionButton.disabled = true;
        }
        renderWorkflowSummary();
        return;
    }

    elements.sessionInfo.classList.remove("hidden");

    if (elements.sessionId) {
        elements.sessionId.textContent = appState.session.id;
    }
    if (elements.sessionActiveSources) {
        elements.sessionActiveSources.textContent =
            appState.session.actualActiveSources.join(", ") || "-";
    }
    if (elements.sessionParticipantsSummary) {
        elements.sessionParticipantsSummary.textContent =
            appState.session.participants.join(", ")
            || appState.session.participantsText
            || "직접 입력 없음";
    }

    const sessionStatusMap = {
        draft: ["준비됨", "idle"],
        running: ["진행 중", "live"],
        ended: ["종료됨", "idle"],
        archived: ["보관됨", "idle"],
    };
    const [label, tone] =
        sessionStatusMap[appState.session.status] ?? [appState.session.status, "idle"];
    setStatus(elements.sessionStatus, label, tone);

    if (elements.endSessionButton) {
        elements.endSessionButton.disabled = appState.session.status !== "running";
    }

    renderWorkflowSummary();
}

export function resetReportState() {
    appState.report.latestReportId = null;
    appState.report.latestReportType = null;
    appState.report.latestVersion = null;
    appState.report.latestPath = null;
    appState.report.status = "idle";
    elements.reportFilePath.textContent = "";
    elements.reportVersion.textContent = "-";
    setStatus(elements.reportStatus, "생성 대기", "idle");
    renderWorkflowSummary();
}
