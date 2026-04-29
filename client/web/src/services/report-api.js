import { 
  fetchRecentReports as fetchSharedRecentReports,
  fetchReportDetail as fetchSharedReportDetail,
  fetchReportDocument as fetchSharedReportDocument,
  fetchLatestReport as fetchSharedLatestReport,
  fetchFinalReportStatus as fetchSharedFinalReportStatus,
  enqueueReportGenerationJob as enqueueSharedReportGenerationJob,
  fetchReportGenerationJob as fetchSharedReportGenerationJob,
  saveReportDocument as saveSharedReportDocument,
  buildReportArtifactUrl as buildSharedReportArtifactUrl
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

export function fetchReportDocument(options) {
  return fetchSharedReportDocument({
    buildApiUrl,
    ...options,
  });
}

export function saveReportDocument(options) {
  return saveSharedReportDocument({
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

export function buildReportArtifactUrl(options) {
  return buildSharedReportArtifactUrl({
    buildApiUrl,
    ...options,
  });
}
