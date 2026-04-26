/** 워크스페이스 화면이 쓰는 세션/리포트 상태 해석 API를 한곳에서 내보내는 배럴 파일이다. */

export {
  formatDateTime,
  formatFullDateTime,
  formatSourceLabel,
  getSessionStatusLabel,
  isLiveSession,
  isRecoveryRequiredSession,
  normalizeStatus,
} from "./workspace-formatters.js";

export {
  getMeetingStatusLabel,
  getMeetingStatusTone,
  getReportStatusLabel,
  getReportStatusTone,
  getWorkflowListLabel,
  groupSessionsByOperationalState,
  resolveMeetingWorkflowStatus,
  resolveWorkflowStatus,
  sortSessionsByStartedAt,
} from "./workspace-workflow.js";
