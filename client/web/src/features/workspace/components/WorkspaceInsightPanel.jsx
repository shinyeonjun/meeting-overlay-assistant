import React from "react";

import {
  buildStatusCopy,
  buildSummaryModel,
  normalizeInsightStatus,
} from "./WorkspaceInsightPanel.helpers.js";
import {
  CompletedInsightContent,
  InsightHeader,
  InsightStatusCard,
} from "./WorkspaceInsightPanel.parts.jsx";

export default function WorkspaceInsightPanel({
  actionNotice,
  hidePreviousNote,
  latestReport,
  overview,
  reportStatus,
  session,
}) {
  const insightStatus = normalizeInsightStatus(overview);
  const summary = buildSummaryModel(overview, session);
  const statusCopy = buildStatusCopy({
    actionNotice,
    hidePreviousNote,
    insightStatus,
    reportStatus,
  });
  const isAnalyzing = insightStatus === "processing" || insightStatus === "pending";
  const headline =
    summary?.headline ||
    latestReport?.title ||
    session?.title ||
    "회의 요약이 아직 없습니다.";
  const showCompletedInsight = !hidePreviousNote && insightStatus === "completed";

  return (
    <aside className="caps-insight-panel">
      <div className="caps-summary-block">
        <InsightHeader reportStatus={reportStatus} session={session} />

        {statusCopy ? (
          <InsightStatusCard
            isAnalyzing={isAnalyzing}
            statusCopy={statusCopy}
            workspaceSummaryStatus={overview?.workspace_summary_status}
          />
        ) : (
          <div className="caps-summary-headline">{headline}</div>
        )}

        {showCompletedInsight ? <CompletedInsightContent summary={summary} /> : null}
      </div>
    </aside>
  );
}
