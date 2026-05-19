import { resolveWorkflowStatus } from "../../app/workspace-model.js";

function getReportTimestamp(report) {
  const value = Date.parse(report?.generated_at ?? "");
  return Number.isNaN(value) ? 0 : value;
}

export function selectLatestReportsBySession(reports) {
  const map = {};
  for (const report of reports) {
    const current = map[report.session_id];
    if (!current) {
      map[report.session_id] = report;
      continue;
    }

    const reportTimestamp = getReportTimestamp(report);
    const currentTimestamp = getReportTimestamp(current);
    if (reportTimestamp > currentTimestamp) {
      map[report.session_id] = report;
      continue;
    }

    if (reportTimestamp === currentTimestamp && String(report.id) > String(current.id)) {
      map[report.session_id] = report;
    }
  }
  return map;
}

export function selectReportReadySessions(sessions, reportStatuses) {
  return sessions.filter(
    (item) => resolveWorkflowStatus(item, reportStatuses[item.id]).category === "ready",
  );
}

export function buildReportDetailConfig(report) {
  return {
    type: "report",
    sessionId: report.session_id,
    reportId: report.id,
  };
}
