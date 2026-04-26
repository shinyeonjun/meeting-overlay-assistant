/** 세션과 회의록의 워크플로 상태를 화면용 상태로 변환하는 모듈이다. */

import {
  isLiveSession,
  isRecoveryRequiredSession,
  normalizeStatus,
} from "./workspace-formatters.js";

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

function buildWorkflowState({ category, label, pipelineStage, status, tone }) {
  return { category, label, pipelineStage, status, tone };
}

function isStalledWarning(reason) {
  return [
    "post_processing_stalled",
    "note_correction_stalled",
    "report_generation_stalled",
  ].includes(normalizeStatus(reason));
}

function isProcessingStatus(status) {
  const normalized = normalizeStatus(status);
  return normalized === "processing" || normalized.startsWith("processing_");
}

export function resolveWorkflowStatus(session, rawReportStatus) {
  if (isRecoveryRequiredSession(session)) {
    return buildWorkflowState({
      category: "recovery_required",
      label: "복구 필요",
      pipelineStage: "recovery",
      status: "recovery_required",
      tone: "failed",
    });
  }

  if (isLiveSession(session?.status)) {
    return buildWorkflowState({
      category: "running",
      label: "진행 중",
      pipelineStage: "live",
      status: "pending",
      tone: "live",
    });
  }

  const reportStatus = normalizeReportStatus(rawReportStatus);
  const pipelineStage = resolvePipelineStage(session, reportStatus);
  const reportState = normalizeStatus(reportStatus.status);
  const warningReason = normalizeStatus(reportStatus.warning_reason);
  const latestJobStatus = normalizeStatus(reportStatus.latest_job_status);
  const noteCorrectionStatus = normalizeStatus(reportStatus.note_correction_job_status);
  const postProcessingStatus = normalizeStatus(
    reportStatus.post_processing_status ?? session?.post_processing_status ?? "not_started",
  );

  if (warningReason === "post_processing_stalled") {
    return buildWorkflowState({
      category: "failed",
      label: "노트 생성 멈춤",
      pipelineStage: "post_processing",
      status: "failed",
      tone: "failed",
    });
  }

  if (warningReason === "note_correction_stalled") {
    return buildWorkflowState({
      category: "failed",
      label: "노트 보정 멈춤",
      pipelineStage: "note_correction",
      status: "failed",
      tone: "failed",
    });
  }

  if (warningReason === "report_generation_stalled") {
    return buildWorkflowState({
      category: "failed",
      label: "회의록 생성 멈춤",
      pipelineStage: "report_generation",
      status: "failed",
      tone: "failed",
    });
  }

  if (pipelineStage === "post_processing") {
    if (postProcessingStatus === "failed" || reportState === "failed") {
      return buildWorkflowState({
        category: "failed",
        label: "노트 생성 실패",
        pipelineStage,
        status: "failed",
        tone: "failed",
      });
    }
    if (isProcessingStatus(postProcessingStatus) || reportState === "processing") {
      return buildWorkflowState({
        category: "processing",
        label: "노트 생성 중",
        pipelineStage,
        status: "processing",
        tone: "processing",
      });
    }
    return buildWorkflowState({
      category: "processing",
      label: "노트 생성 대기",
      pipelineStage,
      status: "pending",
      tone: "pending",
    });
  }

  if (pipelineStage === "note_correction") {
    if (noteCorrectionStatus === "failed" || reportState === "failed") {
      return buildWorkflowState({
        category: "failed",
        label: "노트 보정 실패",
        pipelineStage,
        status: "failed",
        tone: "failed",
      });
    }
    if (noteCorrectionStatus === "processing" || reportState === "processing") {
      return buildWorkflowState({
        category: "processing",
        label: "노트 보정 중",
        pipelineStage,
        status: "processing",
        tone: "processing",
      });
    }
    return buildWorkflowState({
      category: "processing",
      label: "노트 보정 대기",
      pipelineStage,
      status: "pending",
      tone: "pending",
    });
  }

  if (pipelineStage === "report_generation") {
    if (reportState === "completed") {
      return buildWorkflowState({
        category: "completed",
        label: "회의록 완료",
        pipelineStage,
        status: "completed",
        tone: "completed",
      });
    }
    if (reportState === "failed") {
      return buildWorkflowState({
        category: "failed",
        label: "회의록 생성 실패",
        pipelineStage,
        status: "failed",
        tone: "failed",
      });
    }
    if (
      reportState === "processing" ||
      latestJobStatus === "processing" ||
      latestJobStatus === "pending"
    ) {
      return buildWorkflowState({
        category: "processing",
        label: "회의록 생성 중",
        pipelineStage,
        status: "processing",
        tone: "processing",
      });
    }
    return buildWorkflowState({
      category: "ready",
      label: "회의록 생성 대기",
      pipelineStage,
      status: "pending",
      tone: "pending",
    });
  }

  if (reportState === "completed" || pipelineStage === "completed") {
    return buildWorkflowState({
      category: "completed",
      label: "회의록 완료",
      pipelineStage: "completed",
      status: "completed",
      tone: "completed",
    });
  }

  if (reportState === "failed") {
    return buildWorkflowState({
      category: "failed",
      label: "회의록 생성 실패",
      pipelineStage,
      status: "failed",
      tone: "failed",
    });
  }

  return buildWorkflowState({
    category: "ready",
    label: "회의록 생성 대기",
    pipelineStage,
    status: "pending",
    tone: "pending",
  });
}

export function getWorkflowListLabel(session, reportStatus) {
  const workflow = resolveWorkflowStatus(session, reportStatus);
  const warningReason = normalizeStatus(reportStatus?.warning_reason);

  if (workflow.category === "running") {
    return "실시간 캡처 중";
  }
  if (workflow.category === "recovery_required" || workflow.category === "failed") {
    if (isStalledWarning(warningReason)) {
      return "워커 확인 필요";
    }
    return "다시 정리 필요";
  }

  switch (workflow.pipelineStage) {
    case "post_processing":
      return "노트 생성 중";
    case "note_correction":
      return "노트 보정 중";
    case "report_generation":
      return workflow.category === "completed" ? "회의록 완료" : "회의록 생성 중";
    default:
      return workflow.label;
  }
}

export function getReportStatusTone(reportStatus, session = null) {
  return resolveWorkflowStatus(session, reportStatus).tone;
}

export function getReportStatusLabel(reportStatus, session = null) {
  return resolveWorkflowStatus(session, reportStatus).label;
}

export function resolveMeetingWorkflowStatus(session, rawReportStatus) {
  if (isRecoveryRequiredSession(session)) {
    return buildWorkflowState({
      category: "recovery_required",
      label: "복구 필요",
      pipelineStage: "recovery",
      status: "recovery_required",
      tone: "failed",
    });
  }

  if (isLiveSession(session?.status)) {
    return buildWorkflowState({
      category: "running",
      label: "진행 중",
      pipelineStage: "live",
      status: "pending",
      tone: "live",
    });
  }

  const reportStatus = normalizeReportStatus(rawReportStatus);
  const reportState = normalizeStatus(reportStatus.status);
  const warningReason = normalizeStatus(reportStatus.warning_reason);
  const postProcessingStatus = normalizeStatus(
    reportStatus.post_processing_status ?? session?.post_processing_status ?? "not_started",
  );
  const noteCorrectionStatus = normalizeStatus(reportStatus.note_correction_job_status);
  const reportPipelineStage = normalizeStatus(reportStatus.pipeline_stage);

  if (warningReason === "post_processing_stalled") {
    return buildWorkflowState({
      category: "failed",
      label: "정리 멈춤",
      pipelineStage: "post_processing",
      status: "failed",
      tone: "failed",
    });
  }

  if (warningReason === "note_correction_stalled") {
    return buildWorkflowState({
      category: "failed",
      label: "정리 멈춤",
      pipelineStage: "note_correction",
      status: "failed",
      tone: "failed",
    });
  }

  if (postProcessingStatus === "failed") {
    return buildWorkflowState({
      category: "failed",
      label: "정리 실패",
      pipelineStage: "post_processing",
      status: "failed",
      tone: "failed",
    });
  }

  if (
    ["not_started", "queued", "pending"].includes(postProcessingStatus) ||
    isProcessingStatus(postProcessingStatus)
  ) {
    return buildWorkflowState({
      category: "processing",
      label: "정리 중",
      pipelineStage: "post_processing",
      status: isProcessingStatus(postProcessingStatus) ? "processing" : "pending",
      tone: isProcessingStatus(postProcessingStatus) ? "processing" : "pending",
    });
  }

  if (noteCorrectionStatus === "failed") {
    return buildWorkflowState({
      category: "failed",
      label: "정리 실패",
      pipelineStage: "note_correction",
      status: "failed",
      tone: "failed",
    });
  }

  if (
    ["pending", "processing"].includes(noteCorrectionStatus) ||
    (reportPipelineStage === "note_correction" && ["pending", "processing"].includes(reportState))
  ) {
    return buildWorkflowState({
      category: "processing",
      label: "정리 중",
      pipelineStage: "note_correction",
      status:
        noteCorrectionStatus === "processing" || reportState === "processing"
          ? "processing"
          : "pending",
      tone:
        noteCorrectionStatus === "processing" || reportState === "processing"
          ? "processing"
          : "pending",
    });
  }

  return buildWorkflowState({
    category: "completed",
    label: "정리 완료",
    pipelineStage: "completed",
    status: "completed",
    tone: "completed",
  });
}

export function getMeetingStatusTone(reportStatus, session = null) {
  return resolveMeetingWorkflowStatus(session, reportStatus).tone;
}

export function getMeetingStatusLabel(reportStatus, session = null) {
  return resolveMeetingWorkflowStatus(session, reportStatus).label;
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
