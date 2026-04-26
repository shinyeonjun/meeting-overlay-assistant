/**
 * 회의록 상태 표시 전용 컨트롤러.
 * overlay에서는 회의록을 직접 생성하지 않고 상태와 handoff 정보만 보여준다.
 */

import { elements } from "../dom/elements.js";
import { fetchFinalReportStatus } from "../services/api/report-api.js";
import { normalizeFinalReportStatusPayload } from "../services/payload-normalizers.js";
import { appState } from "../state/app-state.js";
import { setStatus } from "./ui-controller.js";
import { renderWorkflowSummary } from "./ui/workflow-summary-controller.js";

export async function refreshReportFinalStatus() {
    if (!appState.session.id) {
        clearRenderedReportStatus();
        renderWorkflowSummary();
        return;
    }

    try {
        const status = normalizeFinalReportStatusPayload(
            await fetchFinalReportStatus(appState.session.id),
        );
        applyReportStatus(status);
    } catch (error) {
        console.error("[CAPS] 회의록 상태 조회 실패:", error);
    }

    renderWorkflowSummary();
}

function applyReportStatus(status) {
    appState.report.status = status.status;
    appState.report.latestReportId = status.latestReportId ?? null;
    appState.report.latestReportType = status.latestReportType ?? null;
    appState.report.latestArtifactId = status.latestFileArtifactId ?? null;
    appState.report.latestPath = status.latestFilePath ?? null;
    appState.report.generatedAt = status.latestGeneratedAt ?? null;
    appState.report.warningReason = status.warningReason ?? null;
    appState.report.latestJobStatus = status.latestJobStatus ?? null;
    appState.report.latestJobErrorMessage = status.latestJobErrorMessage ?? null;

    if (elements.reportFilePath) {
        elements.reportFilePath.textContent = status.latestFileReference
            ? formatReportFileLabel(status.latestFileReference, status.latestReportType)
            : "";
    }
    renderReportWarning(status);

    if (status.status === "completed") {
        const suffix = status.reportCount > 0 ? ` (${status.reportCount})` : "";
        setStatus(elements.reportStatus, `완료${suffix}`, "live");
        return;
    }

    if (status.status === "failed") {
        setStatus(elements.reportStatus, "실패", "error");
        return;
    }

    if (status.status === "processing") {
        setStatus(elements.reportStatus, "생성 중", "idle");
        return;
    }

    setStatus(elements.reportStatus, "생성 대기", "idle");
}

function clearRenderedReportStatus() {
    appState.report.status = "idle";
    appState.report.latestReportId = null;
    appState.report.latestReportType = null;
    appState.report.latestArtifactId = null;
    appState.report.latestPath = null;
    appState.report.generatedAt = null;
    appState.report.warningReason = null;
    appState.report.latestJobStatus = null;
    appState.report.latestJobErrorMessage = null;

    if (elements.reportFilePath) {
        elements.reportFilePath.textContent = "";
    }
    clearReportWarning();
    setStatus(elements.reportStatus, "생성 대기", "idle");
}

function renderReportWarning(status) {
    if (!elements.reportWarning) {
        return;
    }

    const warningText = buildReportWarningText(status);
    if (!warningText) {
        clearReportWarning();
        return;
    }

    elements.reportWarning.textContent = warningText;
    elements.reportWarning.classList.remove("hidden");
}

function clearReportWarning() {
    if (!elements.reportWarning) {
        return;
    }

    elements.reportWarning.textContent = "";
    elements.reportWarning.classList.add("hidden");
}

function buildReportWarningText(status) {
    if (status.status === "completed" && status.warningReason) {
        return `최근 재생성 경고 · ${formatWarningMessage(status.warningReason)}`;
    }

    if (status.status === "failed" && status.latestJobErrorMessage) {
        return `생성 실패 · ${status.latestJobErrorMessage}`;
    }

    return null;
}

function formatWarningMessage(warningReason) {
    const normalized = String(warningReason ?? "").trim();
    if (!normalized) {
        return "최근 재생성 상태를 확인해 주세요.";
    }

    const knownMessages = {
        latest_job_failed: "최근 재생성 작업이 실패했습니다.",
        regenerate_failed: "최근 재생성 작업이 실패했습니다.",
    };
    return knownMessages[normalized] ?? normalized;
}

function formatReportFileLabel(fileReference, reportType) {
    if (!fileReference) {
        return "";
    }

    const parts = String(fileReference).split(/[\\/]/);
    const fileName = parts[parts.length - 1] || fileReference;
    const formatLabel =
        reportType === "markdown" ? "Markdown" : reportType === "pdf" ? "PDF" : "회의록";
    return `${formatLabel} 준비 완료 · ${fileName}`;
}
