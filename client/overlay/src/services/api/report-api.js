import { requestJson } from "./http-client.js";

export async function generateMarkdownReport(sessionId, audioPath = null) {
    const query = audioPath
        ? `?audio_path=${encodeURIComponent(audioPath)}`
        : "";
    return requestJson(
        `/api/v1/reports/${sessionId}/markdown${query}`,
        { method: "POST" },
    );
}

export async function generatePdfReport(sessionId, audioPath = null) {
    const query = audioPath
        ? `?audio_path=${encodeURIComponent(audioPath)}`
        : "";
    return requestJson(
        `/api/v1/reports/${sessionId}/pdf${query}`,
        { method: "POST" },
    );
}

export async function regenerateReports(sessionId, audioPath) {
    const query = audioPath
        ? `?audio_path=${encodeURIComponent(audioPath)}`
        : "";
    return requestJson(`/api/v1/reports/${sessionId}/regenerate${query}`, {
        method: "POST",
    });
}

export async function fetchFinalReportStatus(sessionId) {
    return requestJson(`/api/v1/reports/${sessionId}/final-status`);
}

export async function listRecentReports({
    scope = "mine",
    limit = 12,
    accountId = null,
    contactId = null,
    contextThreadId = null,
} = {}) {
    const query = new URLSearchParams({
        scope,
        limit: String(limit),
    });
    if (accountId) {
        query.set("account_id", accountId);
    }
    if (contactId) {
        query.set("contact_id", contactId);
    }
    if (contextThreadId) {
        query.set("context_thread_id", contextThreadId);
    }
    return requestJson(`/api/v1/reports/?${query.toString()}`);
}

export async function listSharedWithMeReports({ limit = 12 } = {}) {
    const query = new URLSearchParams({
        limit: String(limit),
    });
    return requestJson(`/api/v1/reports/shared-with-me?${query.toString()}`);
}

export async function getReportById(sessionId, reportId) {
    return requestJson(`/api/v1/reports/${sessionId}/${reportId}`);
}

export async function getSharedReportById(reportId) {
    return requestJson(`/api/v1/reports/shared-with-me/${reportId}`);
}

export async function listReportShares(sessionId, reportId) {
    return requestJson(`/api/v1/reports/${sessionId}/${reportId}/shares`);
}

export async function createReportShare(sessionId, reportId, { sharedWithLoginId, note = "" }) {
    return requestJson(`/api/v1/reports/${sessionId}/${reportId}/shares`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            shared_with_login_id: sharedWithLoginId,
            note,
        }),
    });
}
