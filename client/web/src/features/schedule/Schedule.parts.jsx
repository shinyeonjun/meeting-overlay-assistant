import {
  Bot,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  MoreHorizontal,
  Users,
} from "lucide-react";

import {
  formatSourceLabel,
  getMeetingStatusLabel,
  resolveWorkflowStatus,
} from "../../app/workspace-model.js";
import { WORKSPACE_MODES } from "../../app/workspace-modes.js";
import {
  EVENT_TONES,
  WEEKDAY_LABELS,
  formatCardDate,
  formatMonthLabel,
  getSessionDate,
  isSameDay,
} from "./Schedule.helpers.js";

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
        onClick={() => onOpenSession(session.id, WORKSPACE_MODES.notes)}
        type="button"
      >
        노트 열기
      </button>
    </article>
  );
}

export function UpcomingMeetingsSection({
  onOpenSession,
  reportStatuses,
  sessions,
}) {
  return (
    <section className="caps-schedule-upcoming-section side">
      <h2>다가오는 회의</h2>
      <div className="caps-schedule-upcoming-grid">
        {sessions.length > 0 ? (
          sessions.map((session, index) => (
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
  );
}

export function ScheduleCalendarPanel({ allSessions, baseDate, weekDays }) {
  return (
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
          <button className="caps-schedule-today-button" type="button">
            오늘
          </button>
        </div>
        <div className="caps-schedule-view-switch">
          <button className="active" type="button">
            주
          </button>
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
        {weekDays.map((day, dayIndex) => (
          <ScheduleDayCell
            allSessions={allSessions}
            baseDate={baseDate}
            day={day}
            dayIndex={dayIndex}
            key={day.toISOString()}
          />
        ))}
      </div>
    </article>
  );
}

function ScheduleDayCell({ allSessions, baseDate, day, dayIndex }) {
  const dayEvents = allSessions
    .filter((session) => {
      const date = getSessionDate(session);
      return date ? isSameDay(date, day) : false;
    })
    .slice(0, 3);

  return (
    <div
      className={`caps-schedule-day-cell ${
        dayIndex === baseDate.getDay() ? "focused" : ""
      }`}
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
}
