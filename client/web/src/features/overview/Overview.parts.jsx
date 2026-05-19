import {
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  FileText,
  NotebookText,
  RotateCcw,
} from "lucide-react";

import {
  formatDateTime,
  formatSourceLabel,
  getMeetingStatusLabel,
  resolveWorkflowStatus,
} from "../../app/workspace-model.js";
import { WORKSPACE_MODES } from "../../app/workspace-modes.js";

export function DashboardMetric({ label, value }) {
  return (
    <article className="caps-dashboard-metric">
      <strong>{value}</strong>
      <span>{label}</span>
    </article>
  );
}

function MeetingCard({ onOpenNote, onOpenRecap, reportStatus, session }) {
  return (
    <article className="caps-stitch-meeting-card">
      <div className="caps-stitch-meeting-head">
        <strong>{session.title || "제목 없는 회의"}</strong>
        <span>{getMeetingStatusLabel(reportStatus, session)}</span>
      </div>
      <p>
        {formatSourceLabel(session.primary_input_source)} ·{" "}
        {formatDateTime(session.started_at)}
      </p>
      <div className="caps-dashboard-card-actions">
        <button onClick={onOpenNote} type="button">
          <NotebookText size={14} />
          노트 열기
        </button>
        <button onClick={onOpenRecap} type="button">
          <FileText size={14} />
          회의록 열기
        </button>
      </div>
    </article>
  );
}

function ActionQueueItem({ onOpenNote, onOpenRecap, reportStatus, session }) {
  const workflow = resolveWorkflowStatus(session, reportStatus);
  const targetAction =
    workflow.pipelineStage === "report_generation" || workflow.category === "ready"
      ? { label: "회의록 확인", onClick: onOpenRecap }
      : { label: "노트 확인", onClick: onOpenNote };

  return (
    <button className="caps-dashboard-action-row" onClick={targetAction.onClick} type="button">
      <span className={`caps-session-status-pill ${workflow.tone}`}>{workflow.label}</span>
      <strong>{session.title || "제목 없는 회의"}</strong>
      <em>{targetAction.label}</em>
      <ArrowRight size={14} />
    </button>
  );
}

export function ActionQueueSection({ onOpenSession, reportStatuses, sessions }) {
  return (
    <section className="caps-stitch-dashboard-card recent">
      <div className="caps-stitch-card-head">
        <div>
          <span>바로 할 일</span>
          <h2>확인할 작업</h2>
        </div>
        <button
          disabled={!sessions[0]}
          onClick={() => onOpenSession(sessions[0]?.id, WORKSPACE_MODES.notes)}
          type="button"
        >
          노트로 이동
        </button>
      </div>

      <div className="caps-dashboard-action-list">
        {sessions.length > 0 ? (
          sessions.map((session) => (
            <ActionQueueItem
              key={session.id}
              onOpenNote={() => onOpenSession(session.id, WORKSPACE_MODES.notes)}
              onOpenRecap={() => onOpenSession(session.id, WORKSPACE_MODES.recaps)}
              reportStatus={reportStatuses[session.id]}
              session={session}
            />
          ))
        ) : (
          <div className="caps-stitch-empty-card">
            <CheckCircle2 size={19} />
            <p>지금 바로 확인할 작업이 없습니다.</p>
          </div>
        )}
      </div>
    </section>
  );
}

export function UpcomingMeetingsPanel({ onOpenSession, onViewSchedule, sessions }) {
  return (
    <aside className="caps-stitch-dashboard-side">
      <section className="caps-stitch-dashboard-card compact">
        <div className="caps-stitch-card-head">
          <div>
            <span>예정/진행</span>
            <h2>다가오는 회의</h2>
          </div>
          <CalendarDays size={18} />
        </div>
        <div className="caps-stitch-upcoming-list">
          {sessions.length > 0 ? (
            sessions.map((session) => (
              <button
                key={session.id}
                className="caps-stitch-upcoming-card"
                onClick={() => onOpenSession(session.id, WORKSPACE_MODES.notes)}
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
  );
}

export function RecentMeetingsSection({
  onOpenSession,
  onViewRecaps,
  reportStatuses,
  sessions,
}) {
  return (
    <section className="caps-stitch-dashboard-card recent caps-dashboard-recent-section">
      <div className="caps-stitch-card-head">
        <div>
          <span>최근 회의</span>
          <h2>최근 노트와 회의록</h2>
        </div>
        <button onClick={onViewRecaps} type="button">
          회의록 전체 보기
        </button>
      </div>

      <div className="caps-stitch-meeting-list">
        {sessions.length > 0 ? (
          sessions.map((session) => (
            <MeetingCard
              key={session.id}
              onOpenNote={() => onOpenSession(session.id, WORKSPACE_MODES.notes)}
              onOpenRecap={() => onOpenSession(session.id, WORKSPACE_MODES.recaps)}
              reportStatus={reportStatuses[session.id]}
              session={session}
            />
          ))
        ) : (
          <div className="caps-stitch-empty-card">
            <RotateCcw size={19} />
            <p>최근 회의가 없습니다.</p>
          </div>
        )}
      </div>
    </section>
  );
}
