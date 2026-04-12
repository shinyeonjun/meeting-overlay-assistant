/** 웹 클라이언트의 workspace model 모듈이다. */
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
