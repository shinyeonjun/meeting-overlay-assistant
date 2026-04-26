/** 클라이언트에서 세션 메타데이터를 사용자 언어로 해석하는 포맷터 모듈이다. */

export function normalizeStatus(value) {
  return String(value ?? "").toLowerCase();
}

export function isLiveSession(status) {
  return ["live", "running", "active"].includes(normalizeStatus(status));
}

export function isRecoveryRequiredSession(session) {
  return normalizeStatus(session?.status) === "ended" && Boolean(session?.recovery_required);
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
  switch (normalizeStatus(source)) {
    case "microphone":
      return "마이크";
    case "system_audio":
      return "시스템 오디오";
    case "mic_and_audio":
    case "mixed":
      return "혼합 입력";
    case "upload":
      return "업로드 파일";
    default:
      return source || "입력 없음";
  }
}

export function getSessionStatusLabel(sessionOrStatus, recoveryRequired = false) {
  const status =
    typeof sessionOrStatus === "object"
      ? normalizeStatus(sessionOrStatus?.status)
      : normalizeStatus(sessionOrStatus);
  const resolvedRecoveryRequired =
    typeof sessionOrStatus === "object"
      ? Boolean(sessionOrStatus?.recovery_required)
      : Boolean(recoveryRequired);

  if (status === "ended" && resolvedRecoveryRequired) {
    return "복구 필요";
  }
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
      return status || "상태 미확인";
  }
}
