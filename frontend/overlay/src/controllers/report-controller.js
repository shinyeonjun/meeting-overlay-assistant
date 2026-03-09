/**
 * 리포트 컨트롤러
 * 세션 탭 안에서 리포트 생성/조회 상태만 단순하게 다룬다.
 */

import { elements } from "../dom/elements.js";
import {
    fetchFinalReportStatus,
    fetchLatestReport,
    generateMarkdownReport,
    generatePdfReport,
} from "../services/api-client.js";
import {
    normalizeFinalReportStatusPayload,
    normalizeReportPayload,
} from "../services/payload-normalizers.js";
import { appState } from "../state/app-state.js";
import { applyReport } from "../state/report-store.js";
import { openWorkspace, setStatus, flashStatus } from "./ui-controller.js";
import { refreshReportHistory, renderReportPanels } from "./shared-rendering.js";

export async function handleGenerateReport() {
    if (!appState.session.id) {
        flashStatus(elements.reportStatus, "세션이 없습니다.", "error");
        return;
    }

    const selectedFormat = elements.reportFormatSelect?.value ?? "pdf";
    setStatus(elements.reportStatus, "생성 중", "idle");

    try {
        if (selectedFormat === "markdown") {
            const reportPayload = normalizeReportPayload(
                await generateMarkdownReport(appState.session.id),
            );
            applyReport(appState, reportPayload);
            elements.reportFilePath.textContent = reportPayload.filePath ?? "";
            elements.reportVersion.textContent = reportPayload.version ? `v${reportPayload.version}` : "-";
        } else {
            const payload = await generatePdfReport(appState.session.id);
            appState.report.latestReportId = payload.id;
            appState.report.latestReportType = payload.report_type;
            appState.report.latestVersion = payload.version ?? null;
            appState.report.latestPath = payload.file_path;
            appState.report.status = "ready";
            elements.reportFilePath.textContent = payload.file_path ?? "";
            elements.reportVersion.textContent = payload.version ? `v${payload.version}` : "-";
        }

        await refreshReportHistory();
        renderReportPanels();
        setStatus(elements.reportStatus, "완료", "live");
        openWorkspace();
    } catch (error) {
        console.error(error);
        setStatus(elements.reportStatus, "생성 실패", "error");
    }
}

export async function handleLoadLatestReport() {
    if (!appState.session.id) {
        flashStatus(elements.reportStatus, "세션이 없습니다.", "error");
        return;
    }

    try {
        const reportPayload = normalizeReportPayload(await fetchLatestReport(appState.session.id));
        applyReport(appState, reportPayload);
        elements.reportFilePath.textContent = reportPayload.filePath ?? "";
        elements.reportVersion.textContent = reportPayload.version ? `v${reportPayload.version}` : "-";
        renderReportPanels();
        setStatus(elements.reportStatus, "완료", "live");
    } catch (error) {
        console.error(error);
        setStatus(elements.reportStatus, "리포트 없음", "idle");
    }
}

export function setupReportHistoryDelegation() {
    // 리포트 탭 UI를 없앤 상태라 별도 위임 처리 없음
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
                elements.reportFormatSelect.value = status.latestReportType === "markdown" ? "markdown" : "pdf";
            }
        }

        if (status.status === "completed") {
            await refreshReportHistory();
            setStatus(elements.reportStatus, `완료(${status.reportCount})`, "live");
            return;
        }
        if (status.status === "failed") {
            setStatus(elements.reportStatus, "실패", "error");
            return;
        }
        setStatus(elements.reportStatus, status.status === "processing" ? "생성 중" : "대기", "idle");
    } catch (error) {
        console.error(error);
    }
}
