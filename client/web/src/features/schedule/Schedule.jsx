import React, { useMemo } from "react";
import { Settings2 } from "lucide-react";

import {
  addDays,
  dedupeSessions,
  getSessionDate,
  matchesSearch,
  startOfWeek,
} from "./Schedule.helpers.js";
import {
  ScheduleCalendarPanel,
  UpcomingMeetingsSection,
} from "./Schedule.parts.jsx";

export default function Schedule({
  grouped,
  onOpenSession,
  reportStatuses,
  searchQuery,
}) {
  const runningSessions = useMemo(
    () => (grouped.running ?? []).filter((session) => matchesSearch(session, searchQuery)),
    [grouped.running, searchQuery],
  );
  const processingSessions = useMemo(
    () =>
      [...(grouped.processing ?? []), ...(grouped.failed ?? [])]
        .filter((session) => matchesSearch(session, searchQuery)),
    [grouped.failed, grouped.processing, searchQuery],
  );
  const completedSessions = useMemo(
    () =>
      dedupeSessions(grouped.ready ?? [], grouped.completed ?? [])
        .filter((session) => matchesSearch(session, searchQuery)),
    [grouped.completed, grouped.ready, searchQuery],
  );
  const allSessions = useMemo(
    () => dedupeSessions(runningSessions, processingSessions, completedSessions),
    [completedSessions, processingSessions, runningSessions],
  );
  const baseDate = getSessionDate(allSessions[0]) ?? new Date();
  const weekStart = startOfWeek(baseDate);
  const weekDays = Array.from({ length: 7 }, (_, index) => addDays(weekStart, index));
  const upcomingSessions = allSessions.slice(0, 3);

  return (
    <div className="caps-schedule-integration animate-fade-in">
      <header className="caps-schedule-integration-header">
        <div>
          <h1>일정 연동</h1>
          <p>연동된 일정과 CAPS 회의 기록을 기준으로 회의 캡처 흐름을 관리합니다.</p>
        </div>
        <button className="caps-schedule-rule-button" type="button">
          <Settings2 size={16} />
          자동화 규칙
        </button>
      </header>

      <section className="caps-schedule-bento">
        <div className="caps-schedule-left-stack">
          <UpcomingMeetingsSection
            onOpenSession={onOpenSession}
            reportStatuses={reportStatuses}
            sessions={upcomingSessions}
          />
        </div>

        <ScheduleCalendarPanel
          allSessions={allSessions}
          baseDate={baseDate}
          weekDays={weekDays}
        />
      </section>
    </div>
  );
}
