import {
  isLiveSession,
  isRecoveryRequiredSession,
  normalizeStatus,
} from "./workspace-formatters.js";

export function normalizeReportStatus(reportStatus) {
  if (reportStatus && typeof reportStatus === "object") {
    return reportStatus;
  }
  if (typeof reportStatus === "string") {
    return { status: reportStatus };
  }
  return {};
}

export function resolvePipelineStage(session, reportStatus) {
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

export function buildWorkflowState({ category, label, pipelineStage, status, tone }) {
  return { category, label, pipelineStage, status, tone };
}

export function buildRecoveryWorkflowState({ label = "복구 필요" } = {}) {
  return buildWorkflowState({
    category: "recovery_required",
    label,
    pipelineStage: "recovery",
    status: "recovery_required",
    tone: "failed",
  });
}

export function buildLiveWorkflowState({ label = "진행 중" } = {}) {
  return buildWorkflowState({
    category: "running",
    label,
    pipelineStage: "live",
    status: "pending",
    tone: "live",
  });
}

export function isStalledWarning(reason) {
  return [
    "post_processing_stalled",
    "note_correction_stalled",
    "report_generation_stalled",
  ].includes(normalizeStatus(reason));
}

const STALLED_PIPELINE_STAGE_BY_REASON = {
  note_correction_stalled: "note_correction",
  post_processing_stalled: "post_processing",
  report_generation_stalled: "report_generation",
};

export function buildStalledWorkflowState(reason, labelsByReason) {
  const normalizedReason = normalizeStatus(reason);
  const pipelineStage = STALLED_PIPELINE_STAGE_BY_REASON[normalizedReason];
  const label = labelsByReason?.[normalizedReason];
  if (!pipelineStage || !label) {
    return null;
  }
  return buildWorkflowState({
    category: "failed",
    label,
    pipelineStage,
    status: "failed",
    tone: "failed",
  });
}

export function isProcessingStatus(status) {
  const normalized = normalizeStatus(status);
  return normalized === "processing" || normalized.startsWith("processing_");
}
