/** 세션과 회의록의 워크플로 상태를 화면용 상태로 변환하는 모듈이다. */

import {
  isLiveSession,
  isRecoveryRequiredSession,
  normalizeStatus,
} from "./workspace-formatters.js";
import {
  buildDraftWorkflowState,
  buildLiveWorkflowState,
  buildRecoveryWorkflowState,
  buildStalledWorkflowState,
  buildWorkflowState,
  isProcessingStatus,
  isStalledWarning,
  normalizeReportStatus,
  resolvePipelineStage,
} from "./workspace-workflow.helpers.js";

export function resolveWorkflowStatus(session, rawReportStatus) {
  const sessionWorkflow = resolveSessionBoundaryWorkflow(session);
  if (sessionWorkflow) {
    return sessionWorkflow;
  }

  const reportStatus = normalizeReportStatus(rawReportStatus);
  const pipelineStage = resolvePipelineStage(session, reportStatus);
  const pipelineBoundaryWorkflow = resolvePipelineBoundaryWorkflow(pipelineStage);
  if (pipelineBoundaryWorkflow) {
    return pipelineBoundaryWorkflow;
  }

  const reportState = normalizeStatus(reportStatus.status);
  const warningReason = normalizeStatus(reportStatus.warning_reason);
  const latestJobStatus = normalizeStatus(reportStatus.latest_job_status);
  const noteCorrectionStatus = normalizeStatus(reportStatus.note_correction_job_status);
  const postProcessingStatus = normalizeStatus(
    reportStatus.post_processing_status ?? session?.post_processing_status ?? "not_started",
  );

  const stalledWorkflow = buildReportStalledWorkflow(warningReason);
  if (stalledWorkflow) {
    return stalledWorkflow;
  }

  if (warningReason === "report_generation_fallback" && reportState === "completed") {
    return buildWorkflowState({
      category: "completed",
      label: "기본 회의록",
      pipelineStage,
      status: "completed",
      tone: "warning",
    });
  }

  if (pipelineStage === "post_processing") {
    return resolvePostProcessingWorkflow({ pipelineStage, postProcessingStatus, reportState });
  }

  if (pipelineStage === "note_correction") {
    return resolveNoteCorrectionWorkflow({ pipelineStage, noteCorrectionStatus, reportState });
  }

  if (pipelineStage === "report_generation") {
    return resolveReportGenerationWorkflow({ pipelineStage, reportState, latestJobStatus });
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
      return warningReason === "report_generation_fallback" ? "기본 회의록" : workflow.label;
  }
}

export function getReportStatusTone(reportStatus, session = null) {
  return resolveWorkflowStatus(session, reportStatus).tone;
}

export function getReportStatusLabel(reportStatus, session = null) {
  return resolveWorkflowStatus(session, reportStatus).label;
}

export function resolveMeetingWorkflowStatus(session, rawReportStatus) {
  const sessionWorkflow = resolveSessionBoundaryWorkflow(session);
  if (sessionWorkflow) {
    return sessionWorkflow;
  }

  const reportStatus = normalizeReportStatus(rawReportStatus);
  const reportState = normalizeStatus(reportStatus.status);
  const warningReason = normalizeStatus(reportStatus.warning_reason);
  const postProcessingStatus = normalizeStatus(
    reportStatus.post_processing_status ?? session?.post_processing_status ?? "not_started",
  );
  const noteCorrectionStatus = normalizeStatus(reportStatus.note_correction_job_status);
  const reportPipelineStage = normalizeStatus(reportStatus.pipeline_stage);
  const pipelineBoundaryWorkflow = resolvePipelineBoundaryWorkflow(reportPipelineStage);
  if (pipelineBoundaryWorkflow) {
    return pipelineBoundaryWorkflow;
  }

  const stalledWorkflow = buildMeetingStalledWorkflow(warningReason);
  if (stalledWorkflow) {
    return stalledWorkflow;
  }

  if (
    postProcessingStatus === "failed" ||
    ["not_started", "queued", "pending"].includes(postProcessingStatus) ||
    isProcessingStatus(postProcessingStatus)
  ) {
    return resolveMeetingPostProcessingWorkflow(postProcessingStatus);
  }

  if (
    noteCorrectionStatus === "failed" ||
    ["pending", "processing"].includes(noteCorrectionStatus) ||
    (reportPipelineStage === "note_correction" && ["pending", "processing"].includes(reportState))
  ) {
    return resolveMeetingNoteCorrectionWorkflow({ noteCorrectionStatus, reportState });
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
      case "draft":
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

function resolveSessionBoundaryWorkflow(session) {
  if (normalizeStatus(session?.status) === "draft") {
    return buildDraftWorkflowState();
  }
  if (isRecoveryRequiredSession(session)) {
    return buildRecoveryWorkflowState();
  }
  if (isLiveSession(session?.status)) {
    return buildLiveWorkflowState();
  }
  return null;
}

function resolvePipelineBoundaryWorkflow(pipelineStage) {
  if (pipelineStage === "draft") {
    return buildDraftWorkflowState();
  }
  if (pipelineStage === "recovery") {
    return buildRecoveryWorkflowState();
  }
  return null;
}

function buildReportStalledWorkflow(warningReason) {
  return buildStalledWorkflowState(warningReason, {
    note_correction_stalled: "노트 보정 멈춤",
    post_processing_stalled: "노트 생성 멈춤",
    report_generation_stalled: "회의록 생성 멈춤",
  });
}

function buildMeetingStalledWorkflow(warningReason) {
  return buildStalledWorkflowState(warningReason, {
    note_correction_stalled: "정리 멈춤",
    post_processing_stalled: "정리 멈춤",
  });
}

function resolvePostProcessingWorkflow({ pipelineStage, postProcessingStatus, reportState }) {
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

function resolveNoteCorrectionWorkflow({ pipelineStage, noteCorrectionStatus, reportState }) {
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

function resolveReportGenerationWorkflow({ pipelineStage, reportState, latestJobStatus }) {
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

function resolveMeetingPostProcessingWorkflow(postProcessingStatus) {
  if (postProcessingStatus === "failed") {
    return buildWorkflowState({
      category: "failed",
      label: "정리 실패",
      pipelineStage: "post_processing",
      status: "failed",
      tone: "failed",
    });
  }
  const processing = isProcessingStatus(postProcessingStatus);
  return buildWorkflowState({
    category: "processing",
    label: "정리 중",
    pipelineStage: "post_processing",
    status: processing ? "processing" : "pending",
    tone: processing ? "processing" : "pending",
  });
}

function resolveMeetingNoteCorrectionWorkflow({ noteCorrectionStatus, reportState }) {
  if (noteCorrectionStatus === "failed") {
    return buildWorkflowState({
      category: "failed",
      label: "정리 실패",
      pipelineStage: "note_correction",
      status: "failed",
      tone: "failed",
    });
  }
  const processing = noteCorrectionStatus === "processing" || reportState === "processing";
  return buildWorkflowState({
    category: "processing",
    label: "정리 중",
    pipelineStage: "note_correction",
    status: processing ? "processing" : "pending",
    tone: processing ? "processing" : "pending",
  });
}
