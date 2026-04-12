import React from "react";
import {
  ArrowRight,
  FileText,
  MessageSquareText,
  PlayCircle,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

import {
  formatDateTime,
  formatSourceLabel,
  getReportStatusLabel,
  getReportStatusTone,
  getSessionStatusLabel,
} from "../../app/workspace-model.js";
import "./overview.css";

function InboxGroup({
  title,
  description,
  sessions,
  reportStatuses,
  onOpenSession,
  tone,
  actionLabel,
}) {
  return (
    <section className="inbox-group">
      <div className="inbox-group-header">
        <div>
          <strong>{title}</strong>
          <p>{description}</p>
        </div>
        <span>{sessions.length}개</span>
      </div>

      {sessions.length > 0 ? (
        <div className="inbox-group-list">
          {sessions.slice(0, 6).map((session) => {
            const reportStatus = reportStatuses?.[session.id];
            return (
              <button
                key={session.id}
                className="inbox-row"
                onClick={() => onOpenSession(session.id)}
                type="button"
              >
                <div className="inbox-row-copy">
                  <strong>{session.title || "제목 없는 세션"}</strong>
                  <span>
                    {formatSourceLabel(session.primary_input_source)} · {formatDateTime(session.started_at)}
                  </span>
                </div>
                <div className="inbox-row-side">
                  <span className={`status-pill ${tone || getReportStatusTone(reportStatus?.status)}`}>
                    {reportStatus ? getReportStatusLabel(reportStatus.status) : getSessionStatusLabel(session.status)}
                  </span>
                  <span className="inbox-row-action">{actionLabel}</span>
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="inbox-empty">해당 상태의 세션이 없습니다.</div>
      )}
    </section>
  );
}

function NoteSection({ title, items, emptyText, onOpen, renderMeta }) {
  return (
    <section className="note-section">
      <div className="note-section-header">
        <strong>{title}</strong>
        <span>{items.length}개</span>
      </div>

      {items.length > 0 ? (
        <div className="note-list">
          {items.slice(0, 4).map((item) => (
            <button
              key={item.id || item.event_id || item.chunk_id}
              className="note-row"
              onClick={() => onOpen(item)}
              type="button"
            >
              <div className="note-row-copy">
                <strong>{item.title || item.document_title}</strong>
                <span>{renderMeta(item)}</span>
              </div>
              <ArrowRight size={14} />
            </button>
          ))}
        </div>
      ) : (
        <div className="inbox-empty compact">{emptyText}</div>
      )}
    </section>
  );
}

export default function Overview({
  data,
  grouped,
  onOpenSession,
  onOpenDetail,
  onViewReports,
  onViewAssistant,
}) {
  const reportStatuses = data?.reportStatuses ?? {};
  const reports = data?.reports ?? [];
  const retrievalBrief = data?.retrieval_brief?.items ?? [];
  const carryItems = [
    ...(data?.carry_over?.action_items ?? []),
    ...(data?.carry_over?.questions ?? []),
    ...(data?.carry_over?.risks ?? []),
  ];

  return (
    <div className="workspace-overview animate-fade-in">
      <section className="triage-intro">
        <div className="triage-intro-copy">
          <span className="section-kicker">SESSION INBOX</span>
          <h2>회의 세션을 정리해야 할 순서대로 보여주는 운영형 워크스페이스</h2>
          <p>
            통계판보다 중요한 건 지금 처리할 세션이 무엇인지, 다음 행동이 무엇인지 바로 보이는
            구조입니다.
          </p>
        </div>
        <div className="triage-intro-actions">
          <button className="secondary-button" onClick={onViewReports} type="button">
            <FileText size={16} />
            리포트 큐
          </button>
          <button className="ghost-button" onClick={onViewAssistant} type="button">
            <MessageSquareText size={16} />
            검색 열기
          </button>
        </div>
      </section>

      <div className="triage-layout">
        <section className="workspace-panel triage-sheet">
          <div className="triage-sheet-header">
            <div className="panel-title-left">
              <PlayCircle size={16} />
              <h3>오늘의 처리 순서</h3>
            </div>
            <span>진행 중 → 생성 가능 → 처리 중</span>
          </div>

          <InboxGroup
            title="1. 진행 중 세션"
            description="회의 중인 세션은 바로 열어서 흐름을 확인합니다."
            sessions={grouped.running}
            reportStatuses={reportStatuses}
            onOpenSession={onOpenSession}
            tone="live"
            actionLabel="열기"
          />

          <InboxGroup
            title="2. 리포트 생성 가능"
            description="회의는 끝났지만 아직 문서로 넘기지 않은 세션입니다."
            sessions={grouped.ready}
            reportStatuses={reportStatuses}
            onOpenSession={onOpenSession}
            tone="ready"
            actionLabel="검토"
          />

          <InboxGroup
            title="3. 처리 중"
            description="worker가 현재 생성 작업을 진행 중입니다."
            sessions={grouped.processing}
            reportStatuses={reportStatuses}
            onOpenSession={onOpenSession}
            tone="processing"
            actionLabel="상태"
          />
        </section>

        <aside className="triage-notebook">
          <section className="workspace-panel notebook-sheet">
            <div className="triage-sheet-header">
              <div className="panel-title-left">
                <Sparkles size={16} />
                <h3>후속 메모</h3>
              </div>
            </div>
            <NoteSection
              title="Carry-over"
              items={carryItems}
              emptyText="다음 회의로 넘길 항목이 없습니다."
              onOpen={(item) => onOpenSession(item.session_id)}
              renderMeta={(item) => item.session_title}
            />
          </section>

          <section className="workspace-panel notebook-sheet">
            <div className="triage-sheet-header">
              <div className="panel-title-left">
                <FileText size={16} />
                <h3>최근 리포트</h3>
              </div>
            </div>
            <NoteSection
              title="생성된 문서"
              items={reports}
              emptyText="생성된 리포트가 없습니다."
              onOpen={(report) =>
                onOpenDetail({
                  type: "report",
                  sessionId: report.session_id,
                  reportId: report.id,
                })
              }
              renderMeta={(report) => formatDateTime(report.generated_at)}
            />
          </section>

          <section className="workspace-panel notebook-sheet">
            <div className="triage-sheet-header">
              <div className="panel-title-left">
                <ShieldAlert size={16} />
                <h3>최근 검색 브리프</h3>
              </div>
            </div>
            <NoteSection
              title="retrieval"
              items={retrievalBrief}
              emptyText="최근 검색 이력이 없습니다."
              onOpen={(item) => {
                if (item.report_id) {
                  onOpenDetail({
                    type: "report",
                    sessionId: item.session_id,
                    reportId: item.report_id,
                  });
                  return;
                }
                if (item.session_id) {
                  onOpenSession(item.session_id);
                }
              }}
              renderMeta={(item) => `${(Math.max(0, 1 - Number(item.distance)) * 100).toFixed(1)}% 관련`}
            />
          </section>
        </aside>
      </div>
    </div>
  );
}
