export function isLiveSession(status) {
  return ["live", "running", "active"].includes(String(status ?? "").toLowerCase());
}

export function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  try {
    return new Date(value).toLocaleString("ko-KR", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

export function formatFullDateTime(value) {
  if (!value) {
    return "-";
  }

  try {
    return new Date(value).toLocaleString("ko-KR");
  } catch {
    return value;
  }
}

export function formatSourceLabel(source) {
  switch (source) {
    case "microphone":
      return "마이크";
    case "system_audio":
      return "시스템 오디오";
    case "mixed":
      return "혼합 입력";
    case "upload":
      return "업로드 파일";
    default:
      return source || "알 수 없음";
  }
}

export function getSessionStatusLabel(status) {
  if (isLiveSession(status)) {
    return "진행 중";
  }

  switch (status) {
    case "ended":
      return "종료됨";
    case "completed":
      return "완료";
    case "draft":
      return "준비 중";
    default:
      return status || "알 수 없음";
  }
}

export function getReportStatusTone(status) {
  switch (status) {
    case "completed":
      return "completed";
    case "processing":
      return "processing";
    case "pending":
      return "pending";
    case "ready":
      return "ready";
    case "failed":
      return "failed";
    default:
      return "default";
  }
}

export function getReportStatusLabel(status) {
  switch (status) {
    case "completed":
      return "리포트 완료";
    case "processing":
      return "생성 중";
    case "pending":
      return "대기 중";
    case "ready":
      return "생성 가능";
    case "failed":
      return "생성 실패";
    default:
      return "상태 확인 필요";
  }
}

export function sortSessionsByStartedAt(items) {
  return [...(items ?? [])].sort((left, right) => {
    return new Date(right.started_at).getTime() - new Date(left.started_at).getTime();
  });
}

export function groupSessionsByOperationalState(sessions, reportStatuses) {
  const running = [];
  const ready = [];
  const processing = [];
  const completed = [];
  const failed = [];

  for (const session of sessions ?? []) {
    if (isLiveSession(session.status)) {
      running.push(session);
      continue;
    }

    const reportStatus = reportStatuses?.[session.id]?.status;
    if (reportStatus === "completed") {
      completed.push(session);
      continue;
    }
    if (reportStatus === "processing" || reportStatus === "pending") {
      processing.push(session);
      continue;
    }
    if (reportStatus === "failed") {
      failed.push(session);
      continue;
    }
    if (!reportStatus) {
      processing.push(session);
      continue;
    }
    ready.push(session);
  }

  return { running, ready, processing, completed, failed };
}
