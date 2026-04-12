import {
  fetchSessionOverview as fetchSharedSessionOverview,
  fetchSessionTranscript as fetchSharedSessionTranscript,
} from "@caps-client-shared/api/session-api.js";
import { fetchSessionDetail as fetchSharedSessionDetail } from "@caps-client-shared/api/session-detail-api.js";

import { buildApiUrl } from "../config/runtime.js";

async function buildSessionApiError(response, fallbackMessage) {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string" && payload.detail.trim()) {
      return new Error(payload.detail);
    }
  } catch {
    // 응답 본문이 비어 있으면 기본 메시지를 사용한다.
  }
  return new Error(`${fallbackMessage}: ${response.status}`);
}

export function fetchSessionDetail(options) {
  return fetchSharedSessionDetail({
    buildApiUrl,
    ...options,
  });
}

export function fetchSessionOverview(options) {
  return fetchSharedSessionOverview({
    buildApiUrl,
    ...options,
  });
}

export function fetchSessionTranscript(options) {
  return fetchSharedSessionTranscript({
    buildApiUrl,
    ...options,
  });
}

export async function renameSession({ sessionId, title, fetchImpl = fetch }) {
  const response = await fetchImpl(buildApiUrl(`/api/v1/sessions/${sessionId}`), {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) {
    throw await buildSessionApiError(response, "세션 이름 변경 실패");
  }
  return response.json();
}

export async function deleteSession({ sessionId, fetchImpl = fetch }) {
  const response = await fetchImpl(buildApiUrl(`/api/v1/sessions/${sessionId}`), {
    method: "DELETE",
  });
  if (!response.ok) {
    throw await buildSessionApiError(response, "세션 삭제 실패");
  }
}

export async function reprocessSession({ sessionId, fetchImpl = fetch }) {
  const response = await fetchImpl(buildApiUrl(`/api/v1/sessions/${sessionId}/reprocess`), {
    method: "POST",
  });
  if (!response.ok) {
    throw await buildSessionApiError(response, "노트 재생성 요청 실패");
  }
  return response.json();
}
