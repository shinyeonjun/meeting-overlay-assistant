import { buildApiUrl } from "../config/runtime.js";

async function requestJson(url, options = {}) {
    const response = await fetch(buildApiUrl(url), options);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${url}`);
    }
    return response.json();
}

export async function createSession({ title, source }) {
    return requestJson("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            title,
            mode: "meeting",
            source,
        }),
    });
}

export async function endSession(sessionId) {
    return requestJson(`/api/v1/sessions/${sessionId}/end`, {
        method: "POST",
    });
}

export async function fetchOverview(sessionId) {
    return requestJson(`/api/v1/sessions/${sessionId}/overview`);
}

export async function fetchEventList(sessionId, params = {}) {
    const searchParams = new URLSearchParams();
    if (params.eventType) {
        searchParams.set("event_type", params.eventType);
    }
    if (params.state) {
        searchParams.set("state", params.state);
    }
    const query = searchParams.toString();
    return requestJson(`/api/v1/sessions/${sessionId}/events${query ? `?${query}` : ""}`);
}

export async function updateEvent(sessionId, eventId, payload) {
    return requestJson(`/api/v1/sessions/${sessionId}/events/${eventId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export async function transitionEvent(sessionId, eventId, payload) {
    return requestJson(`/api/v1/sessions/${sessionId}/events/${eventId}/transition`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export async function bulkTransitionEvents(sessionId, payload) {
    return requestJson(`/api/v1/sessions/${sessionId}/events/bulk-transition`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export async function deleteEvent(sessionId, eventId) {
    const response = await fetch(buildApiUrl(`/api/v1/sessions/${sessionId}/events/${eventId}`), {
        method: "DELETE",
    });
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: /api/v1/sessions/${sessionId}/events/${eventId}`);
    }
}

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

export async function fetchReportList(sessionId) {
    return requestJson(`/api/v1/reports/${sessionId}`);
}

export async function fetchLatestReport(sessionId) {
    return requestJson(`/api/v1/reports/${sessionId}/latest`);
}

export async function fetchReportById(sessionId, reportId) {
    return requestJson(`/api/v1/reports/${sessionId}/${reportId}`);
}

export async function fetchFinalReportStatus(sessionId) {
    return requestJson(`/api/v1/reports/${sessionId}/final-status`);
}

export async function fetchRuntimeReadiness() {
    return requestJson("/api/v1/runtime/readiness");
}
