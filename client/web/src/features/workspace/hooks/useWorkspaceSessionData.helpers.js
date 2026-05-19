import { buildReportArtifactUrl } from "../../../services/report-api.js";
import { buildApiUrl } from "../../../config/runtime.js";
import { isLiveSession } from "../../../app/workspace-model.js";

/** useWorkspaceSessionData의 polling/상태 판정 helper. */

const POST_PROCESSING_POLL_INTERVAL_MS = 5000;
const REPORT_GENERATION_POLL_INTERVAL_MS = 6000;
export const TRANSCRIPT_BATCH_SIZE = 48;
const WORKSPACE_DEBUG = import.meta.env.DEV;

export function debugWorkspace(event, payload = {}) {
  if (!WORKSPACE_DEBUG) {
    return;
  }
  console.debug("[CAPS][workspace]", event, payload);
}

export function isPostProcessingActive(status) {
  const normalized = String(status ?? "").toLowerCase();
  return (
    normalized === "queued" ||
    normalized === "processing" ||
    normalized.startsWith("processing_")
  );
}

export function isWorkspaceSummaryAnalysisActive(overview) {
  const status = String(overview?.workspace_summary_status?.status ?? "").toLowerCase();
  return status === "pending" || status === "processing";
}

export function shouldClearActionNotice({ overview, reportStatus }) {
  return (
    reportStatus?.status === "completed" ||
    (overview?.session?.post_processing_status &&
      !isPostProcessingActive(overview.session.post_processing_status))
  );
}

export function buildVisibleReportArtifactUrls(report) {
  if (!report?.id || !report?.session_id) {
    return null;
  }

  const base = {
    reportId: report.id,
    sessionId: report.session_id,
  };
  return {
    downloadHref: buildReportArtifactUrl({
      ...base,
      artifactKind: "source",
      download: true,
    }),
    downloadLabel: "회의록 다운",
    htmlHref: buildReportArtifactUrl({ ...base, artifactKind: "html" }),
    previewHref: buildReportArtifactUrl({ ...base, artifactKind: "source" }),
    previewLabel: "미리보기",
    reportType: report.report_type,
  };
}

export function buildSessionViewState({ latestReport, session, sessionId, workflow }) {
  const isLive = isLiveSession(session?.status);
  const canDownloadRecording = Boolean(
    session?.recording_available || session?.recording_artifact_id,
  );
  const downloadHref = canDownloadRecording
    ? buildApiUrl(`/api/v1/sessions/${sessionId}/recording?download=true`)
    : null;
  const hidePreviousNote = shouldHidePreviousNote(workflow);
  const visibleLatestReport = hidePreviousNote ? null : latestReport;

  return {
    canDownloadRecording,
    downloadHref,
    hidePreviousNote,
    isLive,
    reportArtifactUrls: buildVisibleReportArtifactUrls(visibleLatestReport),
    showTranscriptProgressHero: shouldShowTranscriptProgressHero(workflow),
    visibleLatestReport,
  };
}

export function shouldHidePreviousNote(workflow) {
  return (
    ["post_processing", "note_correction"].includes(workflow.pipelineStage) &&
    ["pending", "processing"].includes(workflow.status)
  );
}

export function shouldShowTranscriptProgressHero(workflow) {
  return shouldHidePreviousNote(workflow);
}

export function buildReportGenerationStatus({ current, job, sessionId }) {
  return {
    ...(current ?? {}),
    session_id: sessionId,
    status: "processing",
    pipeline_stage: "report_generation",
    latest_job_status: job.status,
    latest_job_error_message: job.error_message ?? null,
  };
}

export function buildPostProcessingStatus({ current, nextSession, sessionId }) {
  return {
    ...(current ?? {}),
    session_id: sessionId,
    status: "pending",
    pipeline_stage: "post_processing",
    post_processing_status: nextSession.post_processing_status ?? "queued",
    latest_job_status: null,
    latest_job_error_message: null,
  };
}

export function buildPollingPlan({ isLive, overview, reportStatus, workflow }) {
  if (isLive) {
    return null;
  }

  const latestJobStatus = String(reportStatus?.latest_job_status ?? "").toLowerCase();
  if (
    workflow.pipelineStage === "post_processing" &&
    ["pending", "processing"].includes(workflow.status)
  ) {
    return {
      intervalMs: POST_PROCESSING_POLL_INTERVAL_MS,
      loadOptions: {
        includeOverview: false,
        includeTranscript: true,
        includeReportDetail: false,
      },
    };
  }

  if (
    workflow.pipelineStage === "note_correction" &&
    ["pending", "processing"].includes(workflow.status)
  ) {
    return {
      intervalMs: REPORT_GENERATION_POLL_INTERVAL_MS,
      loadOptions: {
        includeOverview: true,
        includeTranscript: true,
        includeReportDetail: false,
      },
    };
  }

  if (
    workflow.pipelineStage === "report_generation" &&
    (["pending", "processing"].includes(workflow.status) ||
      ["pending", "processing"].includes(latestJobStatus))
  ) {
    return {
      intervalMs: REPORT_GENERATION_POLL_INTERVAL_MS,
      loadOptions: {
        includeOverview: true,
        includeTranscript: false,
        includeReportDetail: true,
      },
    };
  }

  if (isWorkspaceSummaryAnalysisActive(overview)) {
    return {
      intervalMs: REPORT_GENERATION_POLL_INTERVAL_MS,
      loadOptions: {
        includeOverview: true,
        includeTranscript: false,
        includeReportDetail: false,
      },
    };
  }

  return null;
}
