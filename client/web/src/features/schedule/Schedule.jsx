import React, { useMemo } from "react";
import {
  Bot,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  MoreHorizontal,
  Settings2,
  Users,
} from "lucide-react";

import {
  formatDateTime,
  formatSourceLabel,
  getMeetingStatusLabel,
  resolveWorkflowStatus,
} from "../../app/workspace-model.js";
import { WORKSPACE_MODES } from "../../app/workspace-modes.js";

const WEEKDAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"];
const EVENT_TONES = ["primary", "indigo", "emerald", "amber", "slate"];

function normalizeSearch(value) {
  return String(value ?? "").trim().toLowerCase();
}

function matchesSearch(session, query) {
  const normalized = normalizeSearch(query);
  if (!normalized) {
    return true;
  }
  return [session.title, session.status, session.primary_input_source]
    .filter(Boolean)
    .join(" ")
    .toLowerCase()
    .includes(normalized);
}

function dedupeSessions(...groups) {
  const seen = new Set();
  return groups
    .flat()
    .filter(Boolean)
    .filter((session) => {
      if (seen.has(session.id)) {
        return false;
      }
      seen.add(session.id);
      return true;
    });
}

function getSessionDate(session) {
  const value = session?.started_at || session?.created_at;
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? date : null;
}

function startOfWeek(date) {
  const next = new Date(date);
  next.setHours(0, 0, 0, 0);
  next.setDate(next.getDate() - next.getDay());
  return next;
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function isSameDay(left, right) {
  return (
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate()
  );
}

function formatMonthLabel(date) {
  return new Intl.DateTimeFormat("ko-KR", {
    month: "long",
    year: "numeric",
  }).format(date);
}

function formatCardDate(date) {
  return new Intl.DateTimeFormat("ko-KR", {
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
  }).format(date);
}

function CalendarEvent({ session, tone }) {
  const date = getSessionDate(session);
  const time = date
    ? new Intl.DateTimeFormat("ko-KR", {
        hour: "2-digit",
        minute: "2-digit",
      }).format(date)
    : "시간 미정";

  return (
    <div className={`caps-schedule-calendar-event ${tone}`}>
      {time} · {session.title || "제목 없는 회의"}
    </div>
  );
}

function UpcomingMeetingCard({ onOpenSession, reportStatus, session, tone }) {
  const workflow = resolveWorkflowStatus(session, reportStatus);
  const date = getSessionDate(session);

  return (
    <article className="caps-schedule-upcoming-card">
      <div className="caps-schedule-upcoming-head">
        <span className={`caps-schedule-time-chip ${tone}`}>
          {date ? formatCardDate(date) : "일정 미정"}
        </span>
        <MoreHorizontal size={18} />
      </div>
      <h4>{session.title || "제목 없는 회의"}</h4>
      <div className="caps-schedule-upcoming-meta">
        <CalendarDays size={14} />
        <span>{formatSourceLabel(session.primary_input_source)}</span>
      </div>
      <div className="caps-schedule-upcoming-meta">
        <Users size={14} />
        <span>{getMeetingStatusLabel(reportStatus, session)}</span>
      </div>
      <button
        className={`caps-schedule-recording-button ${workflow.tone}`}
        onClick={() => onOpenSession(session.id, WORKSPACE_MODES.recaps)}
        type="button"
      >
        회의록 열기
      </button>
    </article>
  );
}

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
  const upcomingSessions = dedupeSessions(runningSessions, processingSessions, completedSessions).slice(0, 3);

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
          <section className="caps-schedule-upcoming-section side">
            <h2>다가오는 회의</h2>
            <div className="caps-schedule-upcoming-grid">
              {upcomingSessions.length > 0 ? (
                upcomingSessions.map((session, index) => (
                  <UpcomingMeetingCard
                    key={session.id}
                    onOpenSession={onOpenSession}
                    reportStatus={reportStatuses[session.id]}
                    session={session}
                    tone={EVENT_TONES[index % EVENT_TONES.length]}
                  />
                ))
              ) : (
                <div className="caps-schedule-empty-wide">
                  <Bot size={18} />
                  <p>표시할 회의 일정이 없습니다.</p>
                </div>
              )}
            </div>
          </section>
        </div>

        <article className="caps-schedule-calendar-panel">
          <div className="caps-schedule-calendar-head">
            <div className="caps-schedule-month-controls">
              <h2>{formatMonthLabel(baseDate)}</h2>
              <div>
                <button type="button" title="이전 주">
                  <ChevronLeft size={17} />
                </button>
                <button type="button" title="다음 주">
                  <ChevronRight size={17} />
                </button>
              </div>
              <button className="caps-schedule-today-button" type="button">오늘</button>
            </div>
            <div className="caps-schedule-view-switch">
              <button className="active" type="button">주</button>
              <button type="button">월</button>
              <button type="button">일</button>
            </div>
          </div>

          <div className="caps-schedule-calendar-grid header">
            {WEEKDAY_LABELS.map((label) => (
              <div key={label}>{label}</div>
            ))}
          </div>
          <div className="caps-schedule-calendar-grid body">
            {weekDays.map((day, dayIndex) => {
              const dayEvents = allSessions
                .filter((session) => {
                  const date = getSessionDate(session);
                  return date ? isSameDay(date, day) : false;
                })
                .slice(0, 3);
              return (
                <div
                  key={day.toISOString()}
                  className={`caps-schedule-day-cell ${dayIndex === baseDate.getDay() ? "focused" : ""}`}
                >
                  <span>{day.getDate()}</span>
                  <div className="caps-schedule-day-events">
                    {dayEvents.map((session, eventIndex) => (
                      <CalendarEvent
                        key={session.id}
                        session={session}
                        tone={EVENT_TONES[(dayIndex + eventIndex) % EVENT_TONES.length]}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </article>

      </section>
    </div>
  );
}
