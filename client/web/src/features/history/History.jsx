import React, { useMemo } from "react";

import {
  selectLatestReportsBySession,
  selectReportReadySessions,
} from "./History.helpers.js";
import {
  HistoryHeading,
  HistoryTable,
  ReadySessionsPanel,
  RecentReportsPanel,
} from "./History.parts.jsx";

export default function History({ data, onOpenSession, onOpenDetail }) {
  const sessions = data?.sessions ?? [];
  const reports = data?.reports ?? [];
  const reportStatuses = data?.reportStatuses ?? {};
  const reportsBySession = useMemo(
    () => selectLatestReportsBySession(reports),
    [reports],
  );
  const readySessions = useMemo(
    () => selectReportReadySessions(sessions, reportStatuses),
    [reportStatuses, sessions],
  );

  return (
    <div className="workspace-history animate-fade-in">
      <HistoryHeading />
      <HistoryTable
        onOpenDetail={onOpenDetail}
        onOpenSession={onOpenSession}
        reportStatuses={reportStatuses}
        reportsBySession={reportsBySession}
        sessions={sessions}
      />
      <section className="workspace-grid">
        <ReadySessionsPanel
          onOpenSession={onOpenSession}
          sessions={readySessions}
        />
        <RecentReportsPanel onOpenDetail={onOpenDetail} reports={reports} />
      </section>
    </div>
  );
}
