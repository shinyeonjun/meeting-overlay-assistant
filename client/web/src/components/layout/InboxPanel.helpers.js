import { resolveMeetingWorkflowStatus } from "../../app/workspace-model.js";

function buildSearchIndex(session) {
  return [session.title, session.status, session.primary_input_source]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

export function filterSessions(sessions, searchQuery) {
  const normalized = searchQuery.trim().toLowerCase();
  if (!normalized) {
    return sessions;
  }

  return sessions.filter((session) => buildSearchIndex(session).includes(normalized));
}

export function buildGroupedLists({ filteredSessions, reportStatuses }) {
  const filteredRunning = [];
  const filteredActionNeeded = [];
  const filteredRecent = [];

  filteredSessions.forEach((session) => {
    const workflow = resolveMeetingWorkflowStatus(session, reportStatuses?.[session.id]);
    if (workflow.category === "running") {
      filteredRunning.push(session);
      return;
    }
    if (
      workflow.category === "processing" ||
      workflow.category === "failed" ||
      workflow.category === "recovery_required"
    ) {
      filteredActionNeeded.push(session);
      return;
    }
    filteredRecent.push(session);
  });

  filteredRecent.splice(18);

  return {
    filteredActionNeeded,
    filteredRecent,
    filteredRunning,
  };
}

export function resolveSessionPrimaryActionState({ mode, reportStatus, session }) {
  const workflow = resolveMeetingWorkflowStatus(session, reportStatus);
  const isRecapsMode = mode === "recaps";
  const hasReport = Boolean(
    reportStatus?.latest_report_id || Number(reportStatus?.report_count ?? 0) > 0,
  );
  const reportPipelineStage = String(reportStatus?.pipeline_stage ?? "").toLowerCase();
  const latestReportJobStatus = String(reportStatus?.latest_job_status ?? "").toLowerCase();
  const isReportGenerationActive =
    isRecapsMode &&
    reportPipelineStage === "report_generation" &&
    ["pending", "processing"].includes(latestReportJobStatus);
  const isReportBlockedByNote =
    isRecapsMode &&
    ["running", "processing", "recovery_required"].includes(workflow.category);
  const isReportBlockedByNoteFailure =
    isRecapsMode && workflow.category === "failed" && reportPipelineStage !== "report_generation";
  const primaryActionDisabled =
    isReportGenerationActive || isReportBlockedByNote || isReportBlockedByNoteFailure;
  const primaryActionLabel = (() => {
    if (!isRecapsMode) {
      return session.recovery_required ? "노트 만들기" : "노트 다시 정리하기";
    }
    if (isReportGenerationActive) {
      return "회의록 생성 중";
    }
    if (workflow.category === "running") {
      return "회의 종료 후 생성";
    }
    if (isReportBlockedByNote) {
      return "노트 정리 후 생성";
    }
    if (isReportBlockedByNoteFailure) {
      return "노트 먼저 정리 필요";
    }
    return hasReport ? "회의록 다시 만들기" : "회의록 만들기";
  })();

  return {
    primaryActionDisabled,
    primaryActionLabel,
    workflow,
  };
}
