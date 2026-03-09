/**
 * 리포트 컨트롤러
 * 세션 탭 안에서 수동 리포트 생성과 상태 표시만 담당한다.
 */

import { elements } from "../dom/elements.js";
import {
    fetchFinalReportStatus,
    generateMarkdownReport,
    generatePdfReport,
} from "../services/api-client.js";
import { normalizeFinalReportStatusPayload } from "../services/payload-normalizers.js";
import { appState } from "../state/app-state.js";
import { openWorkspace, setStatus, flashStatus } from "./ui-controller.js";

export async function handleGenerateReport() {
    if (!appState.session.id) {
        flashStatus(elements.reportStatus, "세션이 없습니다.", "error");
        return;
    }

    const selectedFormat = elements.reportFormatSelect?.value ?? "pdf";
    setStatus(elements.reportStatus, "생성 중", "idle");

    try {
        const payload = selectedFormat === "markdown"
            ? await generateMarkdownReport(appState.session.id)
            : await generatePdfReport(appState.session.id);

        appState.report.latestReportId = payload.id;
        appState.report.latestReportType = payload.report_type;
        appState.report.latestVersion = payload.version ?? null;
        appState.report.latestPath = payload.file_path ?? null;
        appState.report.status = "ready";

        elements.reportFilePath.textContent = payload.file_path ?? "";
        elements.reportVersion.textContent = payload.version ? `v${payload.version}` : "-";
        setStatus(elements.reportStatus, "완료", "live");
        openWorkspace();
    } catch (error) {
        console.error(error);
        setStatus(elements.reportStatus, "생성 실패", "error");
    }
}

export async function refreshReportFinalStatus() {
    if (!appState.session.id) {
        return;
    }

    try {
        const status = normalizeFinalReportStatusPayload(
            await fetchFinalReportStatus(appState.session.id),
        );
        appState.report.status = status.status;

        if (status.latestFilePath) {
            appState.report.latestPath = status.latestFilePath;
            elements.reportFilePath.textContent = status.latestFilePath;
        }

        if (status.latestReportId) {
            appState.report.latestReportId = status.latestReportId;
        }

        if (status.latestReportType) {
            appState.report.latestReportType = status.latestReportType;
            if (elements.reportFormatSelect) {
                elements.reportFormatSelect.value = status.latestReportType === "markdown"
                    ? "markdown"
                    : "pdf";
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
            return;
        }

        if (status.status === "failed") {
            setStatus(elements.reportStatus, "실패", "error");
            return;
        }

        setStatus(
            elements.reportStatus,
            status.status === "processing" ? "생성 중" : "생성 대기",
            "idle",
        );
    } catch (error) {
        console.error(error);
    }
}
