/**
 * 리포트 컨트롤러 — 리포트 생성/조회/경로 복사
 */

import { elements } from "../dom/elements.js";
import {
    fetchFinalReportStatus,
    fetchReportById,
    fetchLatestReport,
    generateMarkdownReport,
    generatePdfReport,
    regenerateReports,
} from "../services/api-client.js";
import {
    normalizeFinalReportStatusPayload,
    normalizeReportPayload,
    normalizeRegenerateReportsPayload,
} from "../services/payload-normalizers.js";
import { appState } from "../state/app-state.js";
import { applyReport, applyReportHistory } from "../state/report-store.js";
import { activateTab, openWorkspace, setStatus, flashStatus } from "./ui-controller.js";
import { refreshReportHistory, renderReportHistory, renderReportPanels } from "./shared-rendering.js";

/* ───────────────────────────────── 리포트 생성 ─── */

/** 마크다운 리포트를 생성하고 결과를 패널에 표시한다. */
export async function handleGenerateReport() {
    if (!appState.session.id) {
        flashStatus(elements.reportStatus, "세션 필요", "error");
        return;
    }

    const audioPath = elements.reportAudioPath.value.trim();
    if (!audioPath) {
        flashStatus(elements.reportStatus, "경로 필요", "error");
        return;
    }

    setStatus(elements.reportStatus, "생성 중", "idle");

    try {
        const reportPayload = normalizeReportPayload(
            await generateMarkdownReport(appState.session.id, audioPath),
        );
        applyReport(appState, reportPayload);

        elements.reportFilePath.textContent = reportPayload.filePath;
        if (elements.reportVersion) {
            elements.reportVersion.textContent = reportPayload.version ? `v${reportPayload.version}` : "-";
        }
        await refreshReportHistory();
        renderReportPanels();

        setStatus(elements.reportStatus, "완료", "live");
        activateTab("report");
        openWorkspace();
    } catch (error) {
        console.error(error);
        setStatus(elements.reportStatus, "생성 실패", "error");
    }
}

/** PDF 리포트를 생성한다. */
export async function handleGeneratePdfReport() {
    if (!appState.session.id) {
        flashStatus(elements.reportStatus, "세션 필요", "error");
        return;
    }

    const audioPath = elements.reportAudioPath.value.trim();
    if (!audioPath) {
        flashStatus(elements.reportStatus, "경로 필요", "error");
        return;
    }

    setStatus(elements.reportStatus, "PDF 생성 중", "idle");

    try {
        const payload = await generatePdfReport(appState.session.id, audioPath);
        appState.report.latestReportId = payload.id;
        appState.report.latestReportType = payload.report_type;
        appState.report.latestVersion = payload.version ?? null;
        appState.report.latestPath = payload.file_path;
        appState.report.status = "ready";
        elements.reportFilePath.textContent = payload.file_path;
        if (elements.reportVersion) {
            elements.reportVersion.textContent = payload.version ? `v${payload.version}` : "-";
        }
        await refreshReportHistory();
        setStatus(elements.reportStatus, "PDF 완료", "live");
        activateTab("report");
        openWorkspace();
    } catch (error) {
        console.error(error);
        setStatus(elements.reportStatus, "PDF 실패", "error");
    }
}

/** 세션의 최신 리포트를 불러와 패널을 갱신한다. */
export async function handleLoadLatestReport() {
    if (!appState.session.id) {
        flashStatus(elements.reportStatus, "세션 필요", "error");
        return;
    }

    setStatus(elements.reportStatus, "조회 중", "idle");
    try {
        const reportPayload = normalizeReportPayload(await fetchLatestReport(appState.session.id));
        applyReport(appState, reportPayload);
        elements.reportFilePath.textContent = reportPayload.filePath ?? "";
        if (elements.reportVersion) {
            elements.reportVersion.textContent = reportPayload.version ? `v${reportPayload.version}` : "-";
        }
        await refreshReportHistory();
        renderReportPanels();
        setStatus(elements.reportStatus, "조회 완료", "live");
        activateTab("report");
        openWorkspace();
    } catch (error) {
        console.error(error);
        setStatus(elements.reportStatus, "리포트 없음", "idle");
    }
}

/* ───────────────────────────────── 경로 복사 ─── */

/** 리포트 파일 경로를 클립보드에 복사한다. */
export async function copyReportPath() {
    if (!appState.report.latestPath && appState.session.id) {
        try {
            const reportPayload = normalizeReportPayload(await fetchLatestReport(appState.session.id));
            applyReport(appState, reportPayload);
            elements.reportFilePath.textContent = reportPayload.filePath ?? "";
        } catch (error) {
            console.error(error);
        }
    }

    if (!appState.report.latestPath) {
        flashStatus(elements.reportStatus, "리포트 필요", "error");
        return;
    }

    await navigator.clipboard.writeText(appState.report.latestPath);
    setStatus(elements.reportStatus, "경로 복사됨", "live");
}

/** markdown/pdf를 새 버전으로 한 번에 재생성한다. */
export async function handleRegenerateReports() {
    if (!appState.session.id) {
        flashStatus(elements.reportStatus, "세션 필요", "error");
        return;
    }

    const audioPath = elements.reportAudioPath.value.trim();
    setStatus(elements.reportStatus, "리포트 재생성 중", "idle");

    try {
        const payload = normalizeRegenerateReportsPayload(
            await regenerateReports(appState.session.id, audioPath || null),
        );
        const latest = payload.items[payload.items.length - 1] ?? null;
        if (latest) {
            appState.report.latestReportId = latest.id;
            appState.report.latestReportType = latest.reportType;
            appState.report.latestVersion = latest.version;
            appState.report.latestPath = latest.filePath;
            elements.reportFilePath.textContent = latest.filePath;
            if (elements.reportVersion) {
                elements.reportVersion.textContent = latest.version ? `v${latest.version}` : "-";
            }
        }
        await refreshReportHistory();
        renderReportHistory();
        setStatus(elements.reportStatus, "리포트 재생성 완료", "live");
    } catch (error) {
        console.error(error);
        setStatus(elements.reportStatus, "리포트 재생성 실패", "error");
    }
}

/** 버전 목록에서 특정 리포트를 불러온다. */
export async function handleSelectReportHistory(reportId) {
    if (!appState.session.id || !reportId) {
        return;
    }

    try {
        const reportPayload = normalizeReportPayload(
            await fetchReportById(appState.session.id, reportId),
        );
        applyReport(appState, reportPayload);
        elements.reportFilePath.textContent = reportPayload.filePath ?? "";
        if (elements.reportVersion) {
            elements.reportVersion.textContent = reportPayload.version ? `v${reportPayload.version}` : "-";
        }
        renderReportPanels();
        activateTab("report");
    } catch (error) {
        console.error(error);
        flashStatus(elements.reportStatus, "리포트 조회 실패", "error");
    }
}

export function setupReportHistoryDelegation() {
    elements.reportHistoryList?.addEventListener("click", (event) => {
        const button = event.target.closest(".report-history-item");
        if (!button) {
            return;
        }
        void handleSelectReportHistory(button.dataset.reportId);
    });
}

/** 리포트 최종 상태를 조회해 배지 텍스트를 갱신한다. */
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
