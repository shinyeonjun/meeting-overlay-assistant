/**
 * 워크스페이스 화면이 공통으로 쓰는 상태 해석 helper를 모아둔다.
 *
 * 서버는 세션 상태, post-processing 상태, note correction 상태,
 * report generation 상태를 각각 따로 내려보낸다. 웹 UI는 이 값을 그대로
 * 쓰기보다 "사용자에게 지금 무엇을 보여줄지" 기준의 workflow 상태로
 * 한 번 더 정규화해서 사용한다.
 */
function normalizeStatus(value) {
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
    return "비정상 종료됨";
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

function normalizeReportStatus(reportStatus) {
  if (reportStatus && typeof reportStatus === "object") {
    return reportStatus;
  }
  if (typeof reportStatus === "string") {
    return { status: reportStatus };
  }
  return {};
}

function resolvePipelineStage(session, reportStatus) {
  // 서버가 명시한 pipeline_stage가 있으면 그 값을 우선 신뢰한다.
  // 없을 때만 세션 상태와 job 상태를 조합해서 화면 단계를 복원한다.
  if (reportStatus.pipeline_stage) {
    return normalizeStatus(reportStatus.pipeline_stage);
  }
  if (isLiveSession(session?.status)) {
    return "live";
  }
  if (isRecoveryRequiredSession(session)) {
    return "recovery";
  }

  const postProcessingStatus = normalizeStatus(
    session?.post_processing_status ?? reportStatus.post_processing_status ?? "not_started",
  );
  if (postProcessingStatus !== "completed") {
    return "post_processing";
  }
  const noteCorrectionStatus = normalizeStatus(reportStatus.note_correction_job_status);
  if (noteCorrectionStatus !== "completed") {
    return "note_correction";
  }
  return "report_generation";
}

export function resolveWorkflowStatus(session, rawReportStatus) {
  // UI는 세부 상태를 그대로 노출하지 않고,
  // running / processing / completed / failed 같은 사용자 중심 상태로
  // 다시 압축해서 사용한다.
  if (isRecoveryRequiredSession(session)) {
    return {
      category: "recovery_required",
      label: "비정상 종료됨",
      tone: "failed",
      pipelineStage: "recovery",
      status: "recovery_required",
    };
  }

  if (isLiveSession(session?.status)) {
    return {
      category: "running",
      label: "진행 중",
      tone: "live",
      pipelineStage: "live",
      status: "pending",
    };
  }

  const reportStatus = normalizeReportStatus(rawReportStatus);
  const pipelineStage = resolvePipelineStage(session, reportStatus);
  const reportState = normalizeStatus(reportStatus.status);
  const latestJobStatus = normalizeStatus(reportStatus.latest_job_status);
  const noteCorrectionStatus = normalizeStatus(reportStatus.note_correction_job_status);
  const postProcessingStatus = normalizeStatus(
    reportStatus.post_processing_status ?? session?.post_processing_status ?? "not_started",
  );

  if (pipelineStage === "post_processing") {
    if (postProcessingStatus === "failed" || reportState === "failed") {
      return {
        category: "failed",
        label: "정리 실패",
        tone: "failed",
        pipelineStage,
        status: "failed",
      };
    }
    if (postProcessingStatus === "processing" || reportState === "processing") {
      return {
        category: "processing",
        label: "정리 중",
        tone: "processing",
        pipelineStage,
        status: "processing",
      };
    }
    return {
      category: "processing",
      label: "정리 대기",
      tone: "pending",
      pipelineStage,
      status: "pending",
    };
  }

  if (pipelineStage === "note_correction") {
    if (noteCorrectionStatus === "failed" || reportState === "failed") {
      return {
        category: "failed",
        label: "노트 보정 실패",
        tone: "failed",
        pipelineStage,
        status: "failed",
      };
    }
    if (noteCorrectionStatus === "processing" || reportState === "processing") {
      return {
        category: "processing",
        label: "노트 보정 중",
        tone: "processing",
        pipelineStage,
        status: "processing",
      };
    }
    return {
      category: "processing",
      label: "노트 보정 대기",
      tone: "pending",
      pipelineStage,
      status: "pending",
    };
  }

  if (pipelineStage === "report_generation") {
    if (reportState === "completed") {
      return {
        category: "completed",
        label: "리포트 완료",
        tone: "completed",
        pipelineStage,
        status: "completed",
      };
    }
    if (reportState === "failed") {
      return {
        category: "failed",
        label: "리포트 생성 실패",
        tone: "failed",
        pipelineStage,
        status: "failed",
      };
    }
    if (
      reportState === "processing" ||
      latestJobStatus === "processing" ||
      latestJobStatus === "pending"
    ) {
      return {
        category: "processing",
        label: "리포트 생성 중",
        tone: "processing",
        pipelineStage,
        status: "processing",
      };
    }
    return {
      category: "ready",
      label: "리포트 대기",
      tone: "pending",
      pipelineStage,
      status: "pending",
    };
  }

  if (reportState === "completed" || pipelineStage === "completed") {
    return {
      category: "completed",
      label: "리포트 완료",
      tone: "completed",
      pipelineStage: "completed",
      status: "completed",
    };
  }

  if (reportState === "failed") {
    return {
      category: "failed",
      label: "리포트 생성 실패",
      tone: "failed",
      pipelineStage,
      status: "failed",
    };
  }

  return {
    category: "ready",
    label: "리포트 대기",
    tone: "pending",
    pipelineStage,
    status: "pending",
  };
}

export function getReportStatusTone(reportStatus, session = null) {
  return resolveWorkflowStatus(session, reportStatus).tone;
}

export function getReportStatusLabel(reportStatus, session = null) {
  return resolveWorkflowStatus(session, reportStatus).label;
}

export function sortSessionsByStartedAt(items) {
  return [...(items ?? [])].sort((left, right) => {
    return new Date(right.started_at).getTime() - new Date(left.started_at).getTime();
  });
}

export function groupSessionsByOperationalState(sessions, reportStatuses) {
  // 최근 세션 목록은 도메인 상태가 아니라 사용자의 작업 맥락 기준으로 묶는다.
  // 예: note_correction 중인 세션은 processing 그룹에 묶어 한 곳에서 보이게 한다.
  const running = [];
  const ready = [];
  const processing = [];
  const completed = [];
  const failed = [];

  for (const session of sessions ?? []) {
    const workflow = resolveWorkflowStatus(session, reportStatuses?.[session.id]);
    switch (workflow.category) {
      case "running":
        running.push(session);
        break;
      case "ready":
        ready.push(session);
        break;
      case "completed":
        completed.push(session);
        break;
      case "failed":
      case "recovery_required":
        failed.push(session);
        break;
      case "processing":
      default:
        processing.push(session);
        break;
    }
  }

  return { running, ready, processing, completed, failed };
}
