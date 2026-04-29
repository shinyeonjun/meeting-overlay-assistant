import React from "react";
import {
  ArrowRight,
  CalendarDays,
  CheckCircle2,
} from "lucide-react";

import {
  formatDateTime,
  formatSourceLabel,
  getMeetingStatusLabel,
} from "../../app/workspace-model.js";
import { WORKSPACE_MODES } from "../../app/workspace-modes.js";
import "./overview.css";

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

function MeetingCard({ actionLabel = "열기", onClick, reportStatus, session }) {
  return (
    <button className="caps-stitch-meeting-card" onClick={onClick} type="button">
      <div className="caps-stitch-meeting-head">
        <strong>{session.title || "제목 없는 회의"}</strong>
        <span>
          {getMeetingStatusLabel(reportStatus, session)}
        </span>
      </div>
      <p>{formatSourceLabel(session.primary_input_source)} · {formatDateTime(session.started_at)}</p>
      <div className="caps-stitch-meeting-foot">
        <span>{actionLabel}</span>
        <ArrowRight size={15} />
      </div>
    </button>
  );
}

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
  const completedSessions = dedupeSessions(grouped.ready ?? [], grouped.completed ?? []).slice(0, 4);
  const upcomingSessions = dedupeSessions(runningSessions, processingSessions).slice(0, 2);

  return (
    <div className="caps-stitch-dashboard animate-fade-in">
      <section className="caps-stitch-dashboard-hero">
        <div>
          <h1>오늘 회의 흐름을 확인합니다.</h1>
          <p>최근 회의록과 예정된 회의를 한 화면에서 정리합니다.</p>
        </div>
      </section>

      <section className="caps-stitch-dashboard-grid">
        <section className="caps-stitch-dashboard-card recent">
          <div className="caps-stitch-card-head">
            <div>
              <span>최근 회의</span>
              <h2>최근 회의</h2>
            </div>
            <button onClick={onViewRecaps} type="button">전체 보기</button>
          </div>

          <div className="caps-stitch-meeting-list">
            {completedSessions.length > 0 ? (
              completedSessions.map((session) => (
                <MeetingCard
                  key={session.id}
                  actionLabel="회의록 열기"
                  onClick={() => onOpenSession(session.id, WORKSPACE_MODES.recaps)}
                  reportStatus={reportStatuses[session.id]}
                  session={session}
                />
              ))
            ) : (
              <div className="caps-stitch-empty-card">
                <CheckCircle2 size={19} />
                <p>최근 회의 리캡이 없습니다.</p>
              </div>
            )}
          </div>
        </section>

        <aside className="caps-stitch-dashboard-side">
          <section className="caps-stitch-dashboard-card compact">
            <div className="caps-stitch-card-head">
              <div>
                <span>예정된 회의</span>
                <h2>예정된 회의</h2>
              </div>
              <CalendarDays size={18} />
            </div>
            <div className="caps-stitch-upcoming-list">
              {upcomingSessions.length > 0 ? (
                upcomingSessions.map((session) => (
                  <button
                    key={session.id}
                    className="caps-stitch-upcoming-card"
                    onClick={() => onOpenSession(session.id, WORKSPACE_MODES.live)}
                    type="button"
                  >
                    <strong>{session.title || "제목 없는 회의"}</strong>
                    <span>{formatDateTime(session.started_at)}</span>
                  </button>
                ))
              ) : (
                <div className="caps-stitch-empty-card small">
                  <p>예정된 회의가 없습니다.</p>
                </div>
              )}
            </div>
            <button className="caps-stitch-secondary-button" onClick={onViewSchedule} type="button">
              전체 일정 열기
            </button>
          </section>

        </aside>
      </section>
    </div>
  );
}
