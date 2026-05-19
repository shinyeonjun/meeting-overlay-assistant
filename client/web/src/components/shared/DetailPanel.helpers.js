import { Download, ExternalLink } from "lucide-react";

import { buildReportArtifactUrl } from "../../services/report-api.js";

export function resolveSessionId(config) {
  return config?.sessionId ?? config?.id ?? null;
}

export function buildReportArtifactLinks(report) {
  if (!report?.session_id || !report?.id) {
    return [];
  }

  const base = {
    reportId: report.id,
    sessionId: report.session_id,
  };
  const isPdf = report.report_type === "pdf";
  return [
    {
      href: buildReportArtifactUrl({ ...base, artifactKind: "source" }),
      icon: ExternalLink,
      label: isPdf ? "PDF 미리보기" : "Markdown 열기",
    },
    {
      href: buildReportArtifactUrl({ ...base, artifactKind: "html" }),
      icon: ExternalLink,
      label: "HTML 회의록",
    },
    {
      href: buildReportArtifactUrl({ ...base, artifactKind: "source", download: true }),
      icon: Download,
      label: isPdf ? "PDF 다운로드" : "Markdown 다운로드",
    },
  ];
}

export function buildReportPreviewUrls(report) {
  if (!report?.session_id || !report?.id) {
    return null;
  }

  const base = {
    reportId: report.id,
    sessionId: report.session_id,
  };
  return {
    htmlHref: buildReportArtifactUrl({ ...base, artifactKind: "html" }),
    sourceHref: buildReportArtifactUrl({ ...base, artifactKind: "source" }),
  };
}
