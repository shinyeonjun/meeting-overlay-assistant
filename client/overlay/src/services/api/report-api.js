import { requestJson } from "./http-client.js";

export async function fetchFinalReportStatus(sessionId) {
    return requestJson(`/api/v1/reports/${sessionId}/final-status`);
}
