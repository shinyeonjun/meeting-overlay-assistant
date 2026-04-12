/**
 * 리포트 컨트롤러.
 * 세션 단위 리포트 생성과 상태 표시를 담당한다.
 */

import { elements } from "../dom/elements.js";
import {
    fetchFinalReportStatus,
    generateMarkdownReport,
    generatePdfReport,
} from "../services/api/report-api.js";
import { normalizeFinalReportStatusPayload } from "../services/payload-normalizers.js";
import { appState } from "../state/app-state.js";
import { refreshHistorySnapshot } from "./history-controller.js";
import { flashStatus, openWorkspace, setStatus } from "./ui-controller.js";
import { renderWorkflowSummary } from "./ui/workflow-summary-controller.js";

export async function handleGenerateReport() {
    if (!appState.session.id) {
        flashStatus(elements.reportStatus, "세션이 없습니다.", "error");
        renderWorkflowSummary();
        return;
    }

    const selectedFormat = elements.reportFormatSelect?.value ?? "pdf";
    setStatus(elements.reportStatus, "생성 중", "idle");
    appState.report.status = "processing";
    renderWorkflowSummary();

    try {
        const payload = selectedFormat === "markdown"
            ? await generateMarkdownReport(appState.session.id)
            : await generatePdfReport(appState.session.id);

        appState.report.latestReportId = payload.id;
        appState.report.latestReportType = payload.report_type;
        appState.report.latestVersion = payload.version ?? null;
        appState.report.latestPath = payload.file_path ?? null;
        appState.report.status = "ready";

        elements.reportFilePath.textContent = formatReportFileLabel(
            payload.file_path,
            payload.report_type,
        );
        elements.reportVersion.textContent = payload.version ? `v${payload.version}` : "-";
        setStatus(elements.reportStatus, "완료", "live");
        renderWorkflowSummary();
        openWorkspace();

        refreshHistorySnapshot().catch((error) => {
            console.warn("[CAPS] 히스토리 갱신 실패:", error);
        });
    } catch (error) {
        console.error(error);
        appState.report.status = "failed";
        setStatus(elements.reportStatus, "생성 실패", "error");
        renderWorkflowSummary();
    }
}

export async function refreshReportFinalStatus() {
    if (!appState.session.id) {
        renderWorkflowSummary();
        return;
    }

    try {
        const status = normalizeFinalReportStatusPayload(
            await fetchFinalReportStatus(appState.session.id),
        );
        appState.report.status = status.status;

        if (status.latestFilePath) {
            appState.report.latestPath = status.latestFilePath;
            elements.reportFilePath.textContent = formatReportFileLabel(
                status.latestFilePath,
                status.latestReportType,
            );
        }

        if (status.latestReportId) {
            appState.report.latestReportId = status.latestReportId;
        }

        if (status.latestReportType) {
            appState.report.latestReportType = status.latestReportType;
            if (elements.reportFormatSelect) {
                elements.reportFormatSelect.value =
                    status.latestReportType === "markdown" ? "markdown" : "pdf";
            }
        }

        if (status.latestGeneratedAt) {
            appState.report.generatedAt = status.latestGeneratedAt;
        }

        if (status.reportCount > 0 && status.latestReportType) {
            appState.report.latestVersion = Math.max(appState.report.latestVersion ?? 0, 1);
        }

        if (status.status === "completed") {
            const suffix = status.reportCount > 0 ? `(${status.reportCount})` : "";
            setStatus(elements.reportStatus, `완료${suffix}`, "live");
            renderWorkflowSummary();
            return;
        }

        if (status.status === "failed") {
            setStatus(elements.reportStatus, "실패", "error");
            renderWorkflowSummary();
            return;
        }

        setStatus(
            elements.reportStatus,
            status.status === "processing" ? "생성 중" : "생성 대기",
            "idle",
        );
        renderWorkflowSummary();
    } catch (error) {
        console.error(error);
        renderWorkflowSummary();
    }
}

function formatReportFileLabel(filePath, reportType) {
    if (!filePath) {
        return "";
    }

    const parts = String(filePath).split(/[\\/]/);
    const fileName = parts[parts.length - 1] || filePath;
    const formatLabel =
        reportType === "markdown" ? "Markdown" : reportType === "pdf" ? "PDF" : "리포트";
    return `${formatLabel} 준비 완료 · ${fileName}`;
}
