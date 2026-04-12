import React, { useMemo } from "react";
import { ArrowRight, FileText, NotebookPen } from "lucide-react";

import {
  formatDateTime,
  formatSourceLabel,
  resolveWorkflowStatus,
} from "../../app/workspace-model.js";
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

function FocusMeetingRow({ session, reportStatuses, onOpenSession }) {
  const workflow = resolveWorkflowStatus(session, reportStatuses?.[session.id]);

  return (
    <button className="simple-home-row" onClick={() => onOpenSession(session.id)} type="button">
      <div className="simple-home-row-copy">
        <strong>{session.title || "제목 없는 회의"}</strong>
        <span>
          {formatSourceLabel(session.primary_input_source)} · {formatDateTime(session.started_at)}
        </span>
      </div>
      <div className="simple-home-row-side">
        <span className={`simple-home-row-badge ${workflow.tone}`}>{workflow.label}</span>
        <ArrowRight size={14} />
      </div>
    </button>
  );
}

function CompactList({ icon: Icon, title, items, emptyText, renderItem }) {
  return (
    <section className="simple-home-card">
      <div className="simple-home-card-header">
        <div className="simple-home-card-title">
          <Icon size={16} />
          <strong>{title}</strong>
        </div>
        <span>{items.length}건</span>
      </div>

      {items.length > 0 ? (
        <div className="simple-home-list">{items.map(renderItem)}</div>
      ) : (
        <div className="simple-home-empty">{emptyText}</div>
      )}
    </section>
  );
}

export default function Overview({
  data,
  grouped,
  onOpenDetail,
  onOpenSession,
  onViewMeetings,
}) {
  const reportStatuses = data?.reportStatuses ?? {};
  const reports = data?.reports ?? [];
  const focusSessions = useMemo(
    () =>
      dedupeSessions(
        grouped.running ?? [],
        grouped.processing ?? [],
        grouped.ready ?? [],
        grouped.failed ?? [],
      ).slice(0, 6),
    [grouped.failed, grouped.processing, grouped.ready, grouped.running],
  );

  const carryItems = useMemo(
    () =>
      [
        ...(data?.carry_over?.action_items ?? []),
        ...(data?.carry_over?.decisions ?? []),
        ...(data?.carry_over?.questions ?? []),
      ].slice(0, 4),
    [data?.carry_over],
  );

  return (
    <div className="simple-home-view animate-fade-in">
      <section className="simple-home-hero">
        <div className="simple-home-copy">
          <span className="section-kicker">WORKSPACE HOME</span>
          <h2>지금 바로 이어서 볼 회의만 먼저 보여드립니다.</h2>
          <p>복잡한 화면은 줄이고, 이어서 처리할 회의와 최근 문서만 남겼습니다.</p>
        </div>

        <div className="simple-home-actions">
          <button className="session-action-button primary" onClick={onViewMeetings} type="button">
            <NotebookPen size={15} />
            회의 열기
          </button>
        </div>
      </section>

      <section className="simple-home-card">
        <div className="simple-home-card-header">
          <div className="simple-home-card-title">
            <NotebookPen size={16} />
            <strong>지금 확인할 회의</strong>
          </div>
          <span>{focusSessions.length}건</span>
        </div>

        {focusSessions.length > 0 ? (
          <div className="simple-home-list">
            {focusSessions.map((session) => (
              <FocusMeetingRow
                key={session.id}
                onOpenSession={onOpenSession}
                reportStatuses={reportStatuses}
                session={session}
              />
            ))}
          </div>
        ) : (
          <div className="simple-home-empty">바로 열 회의가 없습니다.</div>
        )}
      </section>

      <div className="simple-home-grid">
        <CompactList
          emptyText="이어진 메모가 없습니다."
          icon={NotebookPen}
          items={carryItems}
          renderItem={(item) => (
            <button
              key={item.id || item.event_id}
              className="simple-home-row compact"
              onClick={() => onOpenSession(item.session_id)}
              type="button"
            >
              <div className="simple-home-row-copy">
                <strong>{item.title}</strong>
                <span>{item.session_title || "회의 메모"}</span>
              </div>
              <ArrowRight size={14} />
            </button>
          )}
          title="이어진 메모"
        />

        <CompactList
          emptyText="최근 문서가 없습니다."
          icon={FileText}
          items={reports.slice(0, 4)}
          renderItem={(report) => (
            <button
              key={report.id}
              className="simple-home-row compact"
              onClick={() =>
                onOpenDetail({
                  type: "report",
                  sessionId: report.session_id,
                  reportId: report.id,
                })
              }
              type="button"
            >
              <div className="simple-home-row-copy">
                <strong>{report.report_type}</strong>
                <span>{formatDateTime(report.generated_at)}</span>
              </div>
              <ArrowRight size={14} />
            </button>
          )}
          title="최근 문서"
        />
      </div>
    </div>
  );
}
