export const SUGGESTED_QUESTIONS = [
  "지난 회의에서 결정된 다음 할 일은?",
  "아직 남은 질문이나 리스크는?",
  "최근 회의에서 중요한 결정만 정리해줘",
  "공유 전에 확인해야 할 내용은?",
];

export function buildChatRequest(query, searchScope) {
  return {
    query,
    limit: 8,
    accountId: searchScope?.accountId,
    contactId: searchScope?.contactId,
    contextThreadId: searchScope?.contextThreadId,
  };
}

export function formatRelevance(distance) {
  const value = Number(distance);
  if (!Number.isFinite(value)) {
    return null;
  }
  return `${(Math.max(0, 1 - value) * 100).toFixed(1)}%`;
}

export function sourceTypeLabel(sourceType) {
  if (sourceType === "report") {
    return "회의록";
  }
  if (sourceType === "session_summary") {
    return "노트 인사이트";
  }
  return sourceType || "회의 자료";
}

export function buildSourceDetailConfig(item) {
  if (!item?.report_id) {
    return null;
  }
  return {
    type: "report",
    sessionId: item.session_id,
    reportId: item.report_id,
  };
}
