/** 오버레이에서 공통 관련 report api 서비스를 제공한다. */
import { requestJson } from "./http-client.js";

export async function fetchFinalReportStatus(sessionId) {
    return requestJson(`/api/v1/reports/${sessionId}/final-status`);
}
