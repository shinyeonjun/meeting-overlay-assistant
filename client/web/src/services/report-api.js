/** 웹 클라이언트에서 쓰는 공통 API 호출을 담당한다. */
import { 
  fetchRecentReports as fetchSharedRecentReports,
  fetchReportDetail as fetchSharedReportDetail,
  fetchLatestReport as fetchSharedLatestReport,
  fetchFinalReportStatus as fetchSharedFinalReportStatus,
  enqueueReportGenerationJob as enqueueSharedReportGenerationJob,
  fetchReportGenerationJob as fetchSharedReportGenerationJob
} from "@caps-client-shared/api/report-api.js";

import { buildApiUrl } from "../config/runtime.js";

export function fetchRecentReports(options = {}) {
  return fetchSharedRecentReports({
    buildApiUrl,
    ...options,
  });
}

export function fetchReportDetail(options) {
  return fetchSharedReportDetail({
    buildApiUrl,
    ...options,
  });
}

export function fetchLatestReport(options) {
  return fetchSharedLatestReport({
    buildApiUrl,
    ...options,
  });
}

export function fetchFinalReportStatus(options) {
  return fetchSharedFinalReportStatus({
    buildApiUrl,
    ...options,
  });
}

export function enqueueReportGenerationJob(options) {
  return enqueueSharedReportGenerationJob({
    buildApiUrl,
    ...options,
  });
}

export function fetchReportGenerationJob(options) {
  return fetchSharedReportGenerationJob({
    buildApiUrl,
    ...options,
  });
}
