import React from "react";

import { dedupeSessions } from "./Overview.helpers.js";
import {
  ActionQueueSection,
  DashboardMetric,
  RecentMeetingsSection,
  UpcomingMeetingsPanel,
} from "./Overview.parts.jsx";
import "./overview.css";

export default function Overview({
  data,
  grouped,
  onOpenSession,
  onViewRecaps,
  onViewSchedule,
}) {
  const reportStatuses = data?.reportStatuses ?? {};
  const runningSessions = grouped.running ?? [];
  const processingSessions = grouped.processing ?? [];
  const failedSessions = grouped.failed ?? [];
  const readySessions = grouped.ready ?? [];
  const completedSessions = dedupeSessions(grouped.completed ?? [], readySessions).slice(0, 5);
  const actionQueue = dedupeSessions(failedSessions, processingSessions, readySessions).slice(0, 5);
  const upcomingSessions = dedupeSessions(runningSessions, processingSessions).slice(0, 3);

  return (
    <div className="caps-stitch-dashboard animate-fade-in">
      <section className="caps-stitch-dashboard-hero">
        <div>
          <h1>오늘 회의 흐름을 확인합니다.</h1>
          <p>대시보드는 현황만 빠르게 보고, 실제 작업은 노트와 회의록 패널에서 이어갑니다.</p>
        </div>
      </section>

      <section className="caps-dashboard-metrics" aria-label="회의 상태 요약">
        <DashboardMetric label="진행 중" value={runningSessions.length} />
        <DashboardMetric label="정리 중" value={processingSessions.length} />
        <DashboardMetric label="확인 필요" value={failedSessions.length + readySessions.length} />
        <DashboardMetric label="완료" value={grouped.completed?.length ?? 0} />
      </section>

      <section className="caps-stitch-dashboard-grid">
        <ActionQueueSection
          onOpenSession={onOpenSession}
          reportStatuses={reportStatuses}
          sessions={actionQueue}
        />

        <UpcomingMeetingsPanel
          onOpenSession={onOpenSession}
          onViewSchedule={onViewSchedule}
          sessions={upcomingSessions}
        />
      </section>

      <RecentMeetingsSection
        onOpenSession={onOpenSession}
        onViewRecaps={onViewRecaps}
        reportStatuses={reportStatuses}
        sessions={completedSessions}
      />
    </div>
  );
}
